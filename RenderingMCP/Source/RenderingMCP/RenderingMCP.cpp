// Copyright Epic Games, Inc. All Rights Reserved.

#include "RenderingMCP.h"
#include "Modules/ModuleManager.h"

#if WITH_EDITOR
#include "Editor.h"
#include "EpicUnrealMCPBridge.h"
#endif

class FRenderingMCPModule : public FDefaultGameModuleImpl
{
public:
	virtual void StartupModule() override
	{
#if WITH_EDITOR
		if (GIsEditor)
		{
			PostEngineInitHandle = FCoreDelegates::OnPostEngineInit.AddRaw(
				this, &FRenderingMCPModule::HandlePostEngineInit);
		}
#endif
	}

	virtual void ShutdownModule() override
	{
#if WITH_EDITOR
		if (PostEngineInitHandle.IsValid())
		{
			FCoreDelegates::OnPostEngineInit.Remove(PostEngineInitHandle);
			PostEngineInitHandle.Reset();
		}
#endif
	}

#if WITH_EDITOR
private:
	void HandlePostEngineInit()
	{
		if (PostEngineInitHandle.IsValid())
		{
			FCoreDelegates::OnPostEngineInit.Remove(PostEngineInitHandle);
			PostEngineInitHandle.Reset();
		}

		FModuleManager::Get().LoadModule(TEXT("UnrealMCP"));
		UE_LOG(LogTemp, Display, TEXT("RenderingMCP: Forced UnrealMCP module load"));

		if (GEditor != nullptr)
		{
			GEditor->GetEditorSubsystem<UEpicUnrealMCPBridge>();
			UE_LOG(LogTemp, Display, TEXT("RenderingMCP: Requested UnrealMCP editor subsystem"));
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("RenderingMCP: GEditor is null after post engine init"));
		}
	}

	FDelegateHandle PostEngineInitHandle;
#endif
};

IMPLEMENT_PRIMARY_GAME_MODULE(FRenderingMCPModule, RenderingMCP, "RenderingMCP");
