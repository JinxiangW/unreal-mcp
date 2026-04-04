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
    constexpr int32 HeaderSizeBytes = 4;
    constexpr int32 MaxRequestSizeBytes = 4 * 1024 * 1024;

    uint32 DecodeMessageLength(const uint8* HeaderBytes)
    {
        return (static_cast<uint32>(HeaderBytes[0]) << 24) |
               (static_cast<uint32>(HeaderBytes[1]) << 16) |
               (static_cast<uint32>(HeaderBytes[2]) << 8) |
               static_cast<uint32>(HeaderBytes[3]);
    }

    void EncodeMessageLength(uint32 MessageLength, uint8* HeaderBytes)
    {
        HeaderBytes[0] = static_cast<uint8>((MessageLength >> 24) & 0xFF);
        HeaderBytes[1] = static_cast<uint8>((MessageLength >> 16) & 0xFF);
        HeaderBytes[2] = static_cast<uint8>((MessageLength >> 8) & 0xFF);
        HeaderBytes[3] = static_cast<uint8>(MessageLength & 0xFF);
    }

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

    while (bRunning && InClientSocket.IsValid())
    {
        uint8 HeaderBytes[HeaderSizeBytes];
        if (!ReceiveExact(InClientSocket, HeaderBytes, HeaderSizeBytes))
        {
            break;
        }

        const uint32 RequestSizeBytes = DecodeMessageLength(HeaderBytes);
        if (RequestSizeBytes == 0 || RequestSizeBytes > MaxRequestSizeBytes)
        {
            UE_LOG(LogTemp, Error, TEXT("MCPServerRunnable: Invalid request size %u bytes"), RequestSizeBytes);
            SendResponse(InClientSocket, MakeErrorResponse(TEXT("Invalid request size")));
            break;
        }

        TArray<uint8> RequestBytes;
        RequestBytes.SetNumUninitialized(static_cast<int32>(RequestSizeBytes));
        if (!ReceiveExact(InClientSocket, RequestBytes.GetData(), static_cast<int32>(RequestSizeBytes)))
        {
            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Client disconnected before request payload completed"));
            break;
        }

        TSharedPtr<FJsonObject> JsonObject;
        FString RequestText;
        if (!TryParseBufferedRequest(RequestBytes, JsonObject, RequestText))
        {
            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Invalid JSON request payload"));
            SendResponse(InClientSocket, MakeErrorResponse(TEXT("Invalid JSON request payload")));
            break;
        }

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
    const int32 PayloadSize = UTF8Response.Length();
    uint8 HeaderBytes[HeaderSizeBytes];
    EncodeMessageLength(static_cast<uint32>(PayloadSize), HeaderBytes);

    int32 HeaderBytesSent = 0;
    while (HeaderBytesSent < HeaderSizeBytes)
    {
        int32 BytesSent = 0;
        if (!Client->Send(HeaderBytes + HeaderBytesSent, HeaderSizeBytes - HeaderBytesSent, BytesSent))
        {
            const int32 LastError = (int32)ISocketSubsystem::Get()->GetLastErrorCode();
            UE_LOG(LogTemp, Error, TEXT("MCPServerRunnable: Failed to send response header after %d/%d bytes - Error code: %d"),
                   HeaderBytesSent, HeaderSizeBytes, LastError);
            return false;
        }
        HeaderBytesSent += BytesSent;
    }

    int32 TotalBytesSent = 0;
    while (TotalBytesSent < PayloadSize)
    {
        int32 BytesSent = 0;
        if (!Client->Send(DataToSend + TotalBytesSent, PayloadSize - TotalBytesSent, BytesSent))
        {
            const int32 LastError = (int32)ISocketSubsystem::Get()->GetLastErrorCode();
            UE_LOG(LogTemp, Error, TEXT("MCPServerRunnable: Failed to send response payload after %d/%d bytes - Error code: %d"),
                   TotalBytesSent, PayloadSize, LastError);
            return false;
        }

        TotalBytesSent += BytesSent;
    }

    UE_LOG(LogTemp, Verbose, TEXT("MCPServerRunnable: Response sent successfully (%d bytes)"),
           TotalBytesSent);
    return true;
}

bool FMCPServerRunnable::ReceiveExact(TSharedPtr<FSocket> Client, uint8* Buffer, int32 BytesToRead) const
{
    if (!Client.IsValid() || Buffer == nullptr || BytesToRead <= 0)
    {
        return false;
    }

    int32 TotalBytesRead = 0;
    while (TotalBytesRead < BytesToRead)
    {
        int32 BytesRead = 0;
        if (!Client->Recv(Buffer + TotalBytesRead, BytesToRead - TotalBytesRead, BytesRead))
        {
            const int32 LastError = (int32)ISocketSubsystem::Get()->GetLastErrorCode();
            if (LastError == SE_EINTR)
            {
                continue;
            }

            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Socket receive failed after %d/%d bytes - Error code: %d"),
                   TotalBytesRead, BytesToRead, LastError);
            return false;
        }

        if (BytesRead <= 0)
        {
            return false;
        }

        TotalBytesRead += BytesRead;
    }

    return true;
}
