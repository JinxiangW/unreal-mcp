#include "MCPServerRunnable.h"
#include "EpicUnrealMCPBridge.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "JsonObjectConverter.h"
#include "Misc/ScopeLock.h"
#include "HAL/PlatformTime.h"

namespace
{
    constexpr int32 SocketBufferSize = 65536;
    constexpr int32 ReceiveBufferSize = 8192;
    constexpr int32 MaxRequestSizeBytes = 4 * 1024 * 1024;

    FString MakeErrorResponse(const FString& ErrorMessage)
    {
        TSharedPtr<FJsonObject> ResponseJson = MakeShared<FJsonObject>();
        ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
        ResponseJson->SetStringField(TEXT("error"), ErrorMessage);

        FString ResultString;
        TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&ResultString);
        FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
        return ResultString;
    }
}

FMCPServerRunnable::FMCPServerRunnable(UEpicUnrealMCPBridge* InBridge, TSharedPtr<FSocket> InListenerSocket)
    : Bridge(InBridge)
    , ListenerSocket(InListenerSocket)
    , bRunning(true)
{
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Created server runnable"));
}

FMCPServerRunnable::~FMCPServerRunnable()
{
    // Note: We don't delete the sockets here as they're owned by the bridge
}

bool FMCPServerRunnable::Init()
{
    return true;
}

uint32 FMCPServerRunnable::Run()
{
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Server thread starting..."));
    
    while (bRunning)
    {
        bool bPending = false;
        if (ListenerSocket->HasPendingConnection(bPending) && bPending)
        {
            ClientSocket = MakeShareable(ListenerSocket->Accept(TEXT("MCPClient")));
            if (ClientSocket.IsValid())
            {
                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Client connection accepted"));
                
                // Set socket options to improve connection stability
                ClientSocket->SetNoDelay(true);
                int32 ActualSocketBufferSize = SocketBufferSize;
                ClientSocket->SetSendBufferSize(SocketBufferSize, ActualSocketBufferSize);
                ClientSocket->SetReceiveBufferSize(SocketBufferSize, ActualSocketBufferSize);
                HandleClientConnection(ClientSocket);
                ClientSocket.Reset();
            }
            else
            {
                UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to accept client connection"));
            }
        }
        
        // Small sleep to prevent tight loop
        FPlatformProcess::Sleep(0.1f);
    }
    
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Server thread stopping"));
    return 0;
}

void FMCPServerRunnable::Stop()
{
    bRunning = false;
}

void FMCPServerRunnable::Exit()
{
}

void FMCPServerRunnable::HandleClientConnection(TSharedPtr<FSocket> InClientSocket)
{
    if (!InClientSocket.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("MCPServerRunnable: Invalid client socket passed to HandleClientConnection"));
        return;
    }

    InClientSocket->SetNonBlocking(false);

    TArray<uint8> RequestBytes;
    RequestBytes.Reserve(ReceiveBufferSize);

    uint8 Buffer[ReceiveBufferSize];
    while (bRunning && InClientSocket.IsValid())
    {
        int32 BytesRead = 0;
        if (InClientSocket->Recv(Buffer, ReceiveBufferSize, BytesRead))
        {
            if (BytesRead == 0)
            {
                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Client disconnected before request completed"));
                break;
            }

            RequestBytes.Append(Buffer, BytesRead);

            if (RequestBytes.Num() > MaxRequestSizeBytes)
            {
                UE_LOG(LogTemp, Error, TEXT("MCPServerRunnable: Request exceeded %d bytes"), MaxRequestSizeBytes);
                SendResponse(InClientSocket, MakeErrorResponse(TEXT("Request too large")));
                break;
            }

            TSharedPtr<FJsonObject> JsonObject;
            FString RequestText;
            if (!TryParseBufferedRequest(RequestBytes, JsonObject, RequestText))
            {
                continue;
            }

            FString LogRequest = RequestText.Len() > 200 ? RequestText.Left(200) + TEXT("...") : RequestText;
            UE_LOG(LogTemp, Verbose, TEXT("MCPServerRunnable: Parsed complete request (%d chars): %s"),
                   RequestText.Len(), *LogRequest);

            FString CommandType;
            if (!JsonObject->TryGetStringField(TEXT("type"), CommandType))
            {
                UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Missing 'type' field in command"));
                SendResponse(InClientSocket, MakeErrorResponse(TEXT("Missing required field: type")));
                break;
            }

            const TSharedPtr<FJsonObject>* ParamsObject = nullptr;
            TSharedPtr<FJsonObject> Params = MakeShared<FJsonObject>();
            if (JsonObject->TryGetObjectField(TEXT("params"), ParamsObject) && ParamsObject && ParamsObject->IsValid())
            {
                Params = *ParamsObject;
            }

            UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Executing command: %s"), *CommandType);
            const FString Response = Bridge->ExecuteCommand(CommandType, Params);
            SendResponse(InClientSocket, Response);
            break;
        }

        const int32 LastError = (int32)ISocketSubsystem::Get()->GetLastErrorCode();
        if (LastError == SE_EWOULDBLOCK)
        {
            FPlatformProcess::Sleep(0.01f);
            continue;
        }

        if (LastError == SE_EINTR)
        {
            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Socket read interrupted, retrying"));
            continue;
        }

        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Client disconnected or socket error. Last error code: %d"),
               LastError);
        break;
    }
}

bool FMCPServerRunnable::TryParseBufferedRequest(const TArray<uint8>& RequestBytes, TSharedPtr<FJsonObject>& OutJsonObject, FString& OutRequestText) const
{
    if (RequestBytes.Num() == 0)
    {
        return false;
    }

    FUTF8ToTCHAR RequestTextConverter(reinterpret_cast<const ANSICHAR*>(RequestBytes.GetData()), RequestBytes.Num());
    OutRequestText = FString(RequestTextConverter.Length(), RequestTextConverter.Get());

    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(OutRequestText);
    if (!FJsonSerializer::Deserialize(Reader, OutJsonObject) || !OutJsonObject.IsValid())
    {
        return false;
    }

    return true;
}

bool FMCPServerRunnable::SendResponse(TSharedPtr<FSocket> Client, const FString& Response) const
{
    if (!Client.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("MCPServerRunnable: Cannot send response on invalid socket"));
        return false;
    }

    const FString LogResponse = Response.Len() > 200 ? Response.Left(200) + TEXT("...") : Response;
    UE_LOG(LogTemp, Verbose, TEXT("MCPServerRunnable: Sending response (%d chars): %s"),
           Response.Len(), *LogResponse);

    FTCHARToUTF8 UTF8Response(*Response);
    const uint8* DataToSend = reinterpret_cast<const uint8*>(UTF8Response.Get());
    int32 TotalDataSize = UTF8Response.Length();
    int32 TotalBytesSent = 0;

    while (TotalBytesSent < TotalDataSize)
    {
        int32 BytesSent = 0;
        if (!Client->Send(DataToSend + TotalBytesSent, TotalDataSize - TotalBytesSent, BytesSent))
        {
            const int32 LastError = (int32)ISocketSubsystem::Get()->GetLastErrorCode();
            UE_LOG(LogTemp, Error, TEXT("MCPServerRunnable: Failed to send response after %d/%d bytes - Error code: %d"),
                   TotalBytesSent, TotalDataSize, LastError);
            return false;
        }

        TotalBytesSent += BytesSent;
    }

    UE_LOG(LogTemp, Verbose, TEXT("MCPServerRunnable: Response sent successfully (%d bytes)"),
           TotalBytesSent);
    return true;
} 
