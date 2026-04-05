// Copyright Epic Games, Inc. All Rights Reserved.

#include "Commands/EpicUnrealMCPMaterialCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceConstant.h"
#include "Materials/MaterialFunction.h"
#include "Materials/MaterialExpression.h"
#include "MaterialExpressionIO.h"
#include "Materials/MaterialExpressionConstant.h"
#include "Materials/MaterialExpressionConstant2Vector.h"
#include "Materials/MaterialExpressionConstant3Vector.h"
#include "Materials/MaterialExpressionConstant4Vector.h"
#include "Materials/MaterialExpressionMultiply.h"
#include "Materials/MaterialExpressionAdd.h"
#include "Materials/MaterialExpressionSubtract.h"
#include "Materials/MaterialExpressionDivide.h"
#include "Materials/MaterialExpressionLinearInterpolate.h"
#include "Materials/MaterialExpressionClamp.h"
#include "Materials/MaterialExpressionTextureSample.h"
#include "Materials/MaterialExpressionTextureCoordinate.h"
#include "Materials/MaterialExpressionTime.h"
#include "Materials/MaterialExpressionSine.h"
#include "Materials/MaterialExpressionCosine.h"
#include "Materials/MaterialExpressionPanner.h"
#include "Materials/MaterialExpressionRotator.h"
#include "Materials/MaterialExpressionPower.h"
#include "Materials/MaterialExpressionAbs.h"
#include "Materials/MaterialExpressionFloor.h"
#include "Materials/MaterialExpressionCeil.h"
#include "Materials/MaterialExpressionFrac.h"
#include "Materials/MaterialExpressionComponentMask.h"
#include "Materials/MaterialExpressionAppendVector.h"
#include "Materials/MaterialExpressionVertexColor.h"
#include "Materials/MaterialExpressionWorldPosition.h"
#include "Materials/MaterialExpressionObjectPositionWS.h"
#include "Materials/MaterialExpressionVertexNormalWS.h"
#include "Materials/MaterialExpressionFresnel.h"
#include "Materials/MaterialExpressionDepthFade.h"
#include "Materials/MaterialExpressionCameraPositionWS.h"
#include "Materials/MaterialExpressionCameraVectorWS.h"
#include "Materials/MaterialExpressionDistance.h"
#include "Materials/MaterialExpressionPixelDepth.h"
#include "Materials/MaterialExpressionSceneDepth.h"
#include "Materials/MaterialExpressionSceneTexture.h"
#include "Materials/MaterialExpressionCustom.h"
#include "Materials/MaterialExpressionScalarParameter.h"
#include "Materials/MaterialExpressionVectorParameter.h"
#include "Materials/MaterialExpressionTextureObjectParameter.h"
#include "Materials/MaterialExpressionTextureSampleParameter2D.h"
#include "Materials/MaterialExpressionStaticBoolParameter.h"
#include "Materials/MaterialExpressionFunctionInput.h"
#include "Materials/MaterialExpressionFunctionOutput.h"
#include "Materials/MaterialExpressionTransform.h"
#include "Materials/MaterialExpressionDotProduct.h"
#include "Materials/MaterialExpressionCrossProduct.h"
#include "Materials/MaterialExpressionOneMinus.h"
#include "Materials/MaterialExpressionNormalize.h"
#include "Materials/MaterialExpressionSaturate.h"
#include "Materials/MaterialExpressionReflectionVectorWS.h"
#include "Materials/MaterialExpressionVertexTangentWS.h"
#include "Materials/MaterialExpressionDesaturation.h"
#include "Materials/MaterialExpressionDDX.h"
#include "Materials/MaterialExpressionDDY.h"
#include "Materials/MaterialExpressionTextureObject.h"
#include "Materials/MaterialExpressionIf.h"
#include "Materials/MaterialExpressionParticleSubUV.h"
#include "Materials/MaterialExpressionLightVector.h"
#include "Materials/MaterialExpressionViewSize.h"
#include "Materials/MaterialExpressionPreSkinnedPosition.h"
#include "Materials/MaterialExpressionPreSkinnedNormal.h"
#include "Materials/MaterialExpressionSquareRoot.h"
#include "Materials/MaterialExpressionMin.h"
#include "Materials/MaterialExpressionMax.h"
#include "Materials/MaterialExpressionRound.h"
#include "Materials/MaterialExpressionSign.h"
#include "Materials/MaterialExpressionStep.h"
#include "Materials/MaterialExpressionSmoothStep.h"
#include "Materials/MaterialExpressionInverseLinearInterpolate.h"
#include "Materials/MaterialExpressionStaticSwitch.h"
#include "Materials/MaterialExpressionDynamicParameter.h"
#include "Materials/MaterialExpressionCurveAtlasRowParameter.h"
#include "Materials/MaterialExpressionReroute.h"
#include "Materials/MaterialExpressionComment.h"
#include "Materials/MaterialExpressionMaterialFunctionCall.h"
#include "Materials/MaterialExpressionLandscapeLayerBlend.h"
#include "Materials/MaterialExpressionObjectOrientation.h"
#include "Factories/MaterialFactoryNew.h"
#include "Factories/TextureFactory.h"
#include "AssetImportTask.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetToolsModule.h"
#include "Engine/Texture.h"
#include "Engine/Texture2D.h"
#include "HAL/PlatformFileManager.h"
#include "UObject/Package.h"

FEpicUnrealMCPMaterialCommands::FEpicUnrealMCPMaterialCommands()
{
}

namespace
{
    EFunctionInputType ResolveFunctionInputType(const FString& RequestedType)
    {
        const FString Normalized = RequestedType.TrimStartAndEnd().ToLower();
        if (Normalized == TEXT("scalar") || Normalized == TEXT("float1") || Normalized == TEXT("float"))
        {
            return FunctionInput_Scalar;
        }
        if (Normalized == TEXT("vector2") || Normalized == TEXT("float2"))
        {
            return FunctionInput_Vector2;
        }
        if (Normalized == TEXT("vector3") || Normalized == TEXT("float3"))
        {
            return FunctionInput_Vector3;
        }
        if (Normalized == TEXT("vector4") || Normalized == TEXT("float4") || Normalized == TEXT("color"))
        {
            return FunctionInput_Vector4;
        }
        if (Normalized == TEXT("texture2d"))
        {
            return FunctionInput_Texture2D;
        }
        if (Normalized == TEXT("texturecube"))
        {
            return FunctionInput_TextureCube;
        }
        if (Normalized == TEXT("texture2darray"))
        {
            return FunctionInput_Texture2DArray;
        }
        if (Normalized == TEXT("volumetexture"))
        {
            return FunctionInput_VolumeTexture;
        }
        if (Normalized == TEXT("staticbool"))
        {
            return FunctionInput_StaticBool;
        }
        if (Normalized == TEXT("materialattributes"))
        {
            return FunctionInput_MaterialAttributes;
        }
        if (Normalized == TEXT("textureexternal"))
        {
            return FunctionInput_TextureExternal;
        }
        if (Normalized == TEXT("bool"))
        {
            return FunctionInput_Bool;
        }
        if (Normalized == TEXT("substrate"))
        {
            return FunctionInput_Substrate;
        }

        return FunctionInput_Scalar;
    }

    ECustomMaterialOutputType ResolveCustomOutputType(const FString& RequestedType)
    {
        const FString Normalized = RequestedType.TrimStartAndEnd().ToLower();
        if (Normalized == TEXT("float2") || Normalized == TEXT("vector2"))
        {
            return CMOT_Float2;
        }
        if (Normalized == TEXT("float3") || Normalized == TEXT("vector3"))
        {
            return CMOT_Float3;
        }
        if (Normalized == TEXT("float4") || Normalized == TEXT("vector4") || Normalized == TEXT("color"))
        {
            return CMOT_Float4;
        }
        if (Normalized == TEXT("materialattributes"))
        {
            return CMOT_MaterialAttributes;
        }

        return CMOT_Float1;
    }

    EMaterialSamplerType ResolveTextureSamplerType(const FString& RequestedSamplerType, UTexture* Texture)
    {
        const FString Normalized = RequestedSamplerType.TrimStartAndEnd().ToLower();

        if (Normalized == TEXT("color"))
        {
            return SAMPLERTYPE_Color;
        }
        if (Normalized == TEXT("linearcolor") || Normalized == TEXT("linear_color"))
        {
            return SAMPLERTYPE_LinearColor;
        }
        if (Normalized == TEXT("normal") || Normalized == TEXT("normalmap") || Normalized == TEXT("normal_map"))
        {
            return SAMPLERTYPE_Normal;
        }
        if (Normalized == TEXT("masks") || Normalized == TEXT("mask"))
        {
            return SAMPLERTYPE_Masks;
        }
        if (Normalized == TEXT("grayscale") || Normalized == TEXT("greyscale"))
        {
            return SAMPLERTYPE_Grayscale;
        }
        if (Normalized == TEXT("alpha"))
        {
            return SAMPLERTYPE_Alpha;
        }
        if (Normalized == TEXT("data"))
        {
            return SAMPLERTYPE_Data;
        }

        if (Texture)
        {
            if (Texture->CompressionSettings == TC_Normalmap)
            {
                return SAMPLERTYPE_Normal;
            }

            return Texture->SRGB ? SAMPLERTYPE_Color : SAMPLERTYPE_LinearColor;
        }

        return SAMPLERTYPE_Color;
    }

    FString SamplerTypeToString(EMaterialSamplerType SamplerType)
    {
        switch (SamplerType)
        {
        case SAMPLERTYPE_Color:
            return TEXT("Color");
        case SAMPLERTYPE_LinearColor:
            return TEXT("LinearColor");
        case SAMPLERTYPE_Normal:
            return TEXT("Normal");
        case SAMPLERTYPE_Masks:
            return TEXT("Masks");
        case SAMPLERTYPE_Grayscale:
            return TEXT("Grayscale");
        case SAMPLERTYPE_Alpha:
            return TEXT("Alpha");
        case SAMPLERTYPE_Data:
            return TEXT("Data");
        default:
            return TEXT("Unknown");
        }
    }

    int32 ParseExplicitOutputIndex(const FString& OutputName)
    {
        if (OutputName.StartsWith(TEXT("Output_")))
        {
            return FCString::Atoi(*OutputName.RightChop(7));
        }

        return INDEX_NONE;
    }
}

TSharedPtr<FJsonObject> FEpicUnrealMCPMaterialCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    // Material creation
    if (CommandType == TEXT("create_material"))
    {
        return HandleCreateMaterial(Params);
    }
    else if (CommandType == TEXT("create_material_function"))
    {
        return HandleCreateMaterialFunction(Params);
    }
    // Material graph operations
    else if (CommandType == TEXT("build_material_graph"))
    {
        return HandleBuildMaterialGraph(Params);
    }
    else if (CommandType == TEXT("get_material_graph"))
    {
        return HandleGetMaterialGraph(Params);
    }
    else if (CommandType == TEXT("set_material_properties"))
    {
        return HandleSetMaterialProperties(Params);
    }
    // Material instance operations
    else if (CommandType == TEXT("create_material_instance"))
    {
        return HandleCreateMaterialInstance(Params);
    }
    else if (CommandType == TEXT("set_material_instance_parameter"))
    {
        return HandleSetMaterialInstanceParameter(Params);
    }
    // Texture operations
    else if (CommandType == TEXT("import_texture"))
    {
        return HandleImportTexture(Params);
    }
    
    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown material command: %s"), *CommandType));
}

// ============================================================================
// Material Creation
// ============================================================================

TSharedPtr<FJsonObject> FEpicUnrealMCPMaterialCommands::HandleCreateMaterial(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString MaterialName;
    if (!Params->TryGetStringField(TEXT("name"), MaterialName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // Check if material already exists
    FString PackagePath = TEXT("/Game/Materials/");
    FString AssetName = MaterialName;
    if (UEditorAssetLibrary::DoesAssetExist(PackagePath + AssetName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Material already exists: %s"), *MaterialName));
    }

    // Create the package
    UPackage* Package = CreatePackage(*(PackagePath + AssetName));
    if (!Package)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package for material"));
    }

    // Create the material using factory
    UMaterialFactoryNew* MaterialFactory = NewObject<UMaterialFactoryNew>();
    UMaterial* NewMaterial = Cast<UMaterial>(MaterialFactory->FactoryCreateNew(
        UMaterial::StaticClass(), Package, *AssetName, RF_Public | RF_Standalone, nullptr, GWarn));
    
    if (!NewMaterial)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create material object"));
    }

    // Add to asset registry
    FAssetRegistryModule::AssetCreated(NewMaterial);
    Package->MarkPackageDirty();

    UE_LOG(LogTemp, Log, TEXT("Successfully created empty material: %s at %s"), *MaterialName, *(PackagePath + AssetName));

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("name"), AssetName);
    ResultObj->SetStringField(TEXT("path"), PackagePath + AssetName);
    ResultObj->SetBoolField(TEXT("success"), true);
    
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPMaterialCommands::HandleCreateMaterialFunction(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString FunctionName;
    if (!Params->TryGetStringField(TEXT("name"), FunctionName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // Get optional path parameter
    FString PackagePath = TEXT("/Game/MaterialFunctions/");
    FString CustomPath;
    if (Params->TryGetStringField(TEXT("path"), CustomPath))
    {
        PackagePath = CustomPath;
        if (!PackagePath.EndsWith(TEXT("/")))
        {
            PackagePath += TEXT("/");
        }
    }

    FString AssetName = FunctionName;
    if (UEditorAssetLibrary::DoesAssetExist(PackagePath + AssetName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Material Function already exists: %s"), *FunctionName));
    }

    // Create the package
    UPackage* Package = CreatePackage(*(PackagePath + AssetName));
    if (!Package)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package for material function"));
    }

    // Create the material function
    UMaterialFunction* NewFunction = NewObject<UMaterialFunction>(Package, *AssetName, RF_Public | RF_Standalone);
    
    if (!NewFunction)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create material function object"));
    }

    // Set description if provided
    FString Description;
    if (Params->TryGetStringField(TEXT("description"), Description))
    {
        NewFunction->Description = Description;
    }

    // Add to asset registry
    FAssetRegistryModule::AssetCreated(NewFunction);
    Package->MarkPackageDirty();
    const FString FunctionAssetPath = PackagePath + AssetName;
    UEditorAssetLibrary::SaveAsset(FunctionAssetPath, false);

    UE_LOG(LogTemp, Log, TEXT("Successfully created material function: %s at %s"), *FunctionName, *FunctionAssetPath);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("name"), AssetName);
    ResultObj->SetStringField(TEXT("path"), FunctionAssetPath);
    ResultObj->SetBoolField(TEXT("success"), true);
    
    return ResultObj;
}

// ============================================================================
// Material Instance Operations
// ============================================================================

TSharedPtr<FJsonObject> FEpicUnrealMCPMaterialCommands::HandleCreateMaterialInstance(const TSharedPtr<FJsonObject>& Params)
{
    // Get parent material path
    FString ParentMaterialPath;
    if (!Params->TryGetStringField(TEXT("parent_material"), ParentMaterialPath))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'parent_material' parameter"));
    }

    // Get optional name
    FString InstanceName;
    if (Params->HasField(TEXT("name")))
    {
        Params->TryGetStringField(TEXT("name"), InstanceName);
    }
    else
    {
        // Generate name from parent material
        FString ParentName = FPaths::GetBaseFilename(ParentMaterialPath);
        InstanceName = TEXT("MI_") + ParentName;
    }

    // Get optional destination path
    FString DestinationPath = TEXT("/Game/Materials/Instances/");
    if (Params->HasField(TEXT("destination_path")))
    {
        Params->TryGetStringField(TEXT("destination_path"), DestinationPath);
    }

    // Ensure destination path exists
    UEditorAssetLibrary::MakeDirectory(DestinationPath);

    // Load parent material
    UMaterialInterface* ParentMaterial = LoadObject<UMaterialInterface>(nullptr, *ParentMaterialPath);
    if (!ParentMaterial)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Failed to load parent material: %s"), *ParentMaterialPath));
    }

    // Create package
    FString PackageName = DestinationPath + InstanceName;
    UPackage* Package = CreatePackage(*PackageName);
    if (!Package)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package"));
    }

    // Create material instance constant
    UMaterialInstanceConstant* MaterialInstance = NewObject<UMaterialInstanceConstant>(Package, *InstanceName, RF_Public | RF_Standalone);
    if (!MaterialInstance)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create material instance"));
    }

    // Set parent
    MaterialInstance->SetParentEditorOnly(ParentMaterial);
    MaterialInstance->PostLoad();

    // Notify asset registry
    FAssetRegistryModule::AssetCreated(MaterialInstance);
    Package->MarkPackageDirty();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("material_instance_path"), MaterialInstance->GetPathName());

    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPMaterialCommands::HandleSetMaterialInstanceParameter(const TSharedPtr<FJsonObject>& Params)
{
    // Get material instance path
    FString MaterialInstancePath;
    if (!Params->TryGetStringField(TEXT("material_instance"), MaterialInstancePath))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'material_instance' parameter"));
    }

    // Get parameter name
    FString ParameterName;
    if (!Params->TryGetStringField(TEXT("parameter_name"), ParameterName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'parameter_name' parameter"));
    }

    // Get parameter type
    FString ParameterType;
    if (!Params->TryGetStringField(TEXT("parameter_type"), ParameterType))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'parameter_type' parameter"));
    }

    // Load material instance
    UMaterialInstanceConstant* MaterialInstance = LoadObject<UMaterialInstanceConstant>(nullptr, *MaterialInstancePath);
    if (!MaterialInstance)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Failed to load material instance: %s"), *MaterialInstancePath));
    }

    FName ParamName(*ParameterName);
    bool bSuccess = false;

    // Set parameter based on type
    if (ParameterType == TEXT("scalar") || ParameterType == TEXT("float"))
    {
        double Value = 0.0;
        if (Params->TryGetNumberField(TEXT("value"), Value))
        {
            MaterialInstance->SetScalarParameterValueEditorOnly(ParamName, static_cast<float>(Value));
            bSuccess = true;
        }
    }
    else if (ParameterType == TEXT("vector") || ParameterType == TEXT("color"))
    {
        const TSharedPtr<FJsonObject>* ValueObj;
        if (Params->TryGetObjectField(TEXT("value"), ValueObj))
        {
            FLinearColor Color(1.0f, 1.0f, 1.0f, 1.0f);
            if ((*ValueObj)->HasField(TEXT("r")))
            {
                double R, G, B, A = 1.0;
                (*ValueObj)->TryGetNumberField(TEXT("r"), R);
                (*ValueObj)->TryGetNumberField(TEXT("g"), G);
                (*ValueObj)->TryGetNumberField(TEXT("b"), B);
                if ((*ValueObj)->HasField(TEXT("a")))
                {
                    (*ValueObj)->TryGetNumberField(TEXT("a"), A);
                }
                Color = FLinearColor(R, G, B, A);
            }
            else
            {
                const TArray<TSharedPtr<FJsonValue>>* ValueArray;
                if ((*ValueObj)->TryGetArrayField(TEXT("value"), ValueArray) && ValueArray->Num() >= 3)
                {
                    double R = (*ValueArray)[0]->AsNumber();
                    double G = (*ValueArray)[1]->AsNumber();
                    double B = (*ValueArray)[2]->AsNumber();
                    double A = ValueArray->Num() > 3 ? (*ValueArray)[3]->AsNumber() : 1.0;
                    Color = FLinearColor(R, G, B, A);
                }
            }
            MaterialInstance->SetVectorParameterValueEditorOnly(ParamName, Color);
            bSuccess = true;
        }
    }
    else if (ParameterType == TEXT("texture"))
    {
        FString TexturePath;
        if (Params->TryGetStringField(TEXT("value"), TexturePath))
        {
            UTexture* Texture = LoadObject<UTexture>(nullptr, *TexturePath);
            if (Texture)
            {
                MaterialInstance->SetTextureParameterValueEditorOnly(ParamName, Texture);
                bSuccess = true;
            }
            else
            {
                return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Failed to load texture: %s"), *TexturePath));
            }
        }
        else
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'value' parameter for texture type"));
        }
    }
    else
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown parameter type: %s"), *ParameterType));
    }

    if (!bSuccess)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to set parameter value"));
    }

    MaterialInstance->PostEditChange();
    MaterialInstance->MarkPackageDirty();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("material_instance_path"), MaterialInstance->GetPathName());

    return ResultObj;
}

// ============================================================================
// Texture Operations
// ============================================================================

TSharedPtr<FJsonObject> FEpicUnrealMCPMaterialCommands::HandleImportTexture(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString SourceFilePath;
    if (!Params->TryGetStringField(TEXT("source_path"), SourceFilePath))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'source_path' parameter"));
    }

    FString TextureName;
    if (!Params->TryGetStringField(TEXT("name"), TextureName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // Get optional parameters
    FString DestinationPath = TEXT("/Game/Textures/");
    FString CustomPath;
    if (Params->TryGetStringField(TEXT("destination_path"), CustomPath))
    {
        DestinationPath = CustomPath;
        if (!DestinationPath.EndsWith(TEXT("/")))
        {
            DestinationPath += TEXT("/");
        }
    }

    bool bDeleteSource = false;
    if (Params->TryGetBoolField(TEXT("delete_source"), bDeleteSource) && bDeleteSource)
    {
        // Will delete after successful import
    }

    // Check if source file exists
    IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();
    if (!PlatformFile.FileExists(*SourceFilePath))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Source file does not exist: %s"), *SourceFilePath));
    }

    // Check if texture already exists
    FString AssetPath = DestinationPath + TextureName;
    if (UEditorAssetLibrary::DoesAssetExist(AssetPath))
    {
        // Delete existing asset
        UEditorAssetLibrary::DeleteAsset(AssetPath);
        UE_LOG(LogTemp, Log, TEXT("Deleted existing texture: %s"), *AssetPath);
    }

    // Import the texture using an automated import task. This matches the safer
    // FBX path and avoids the direct ImportAssets() flow that can recurse into
    // Interchange task processing while we're already running inside a game-thread task.
    UTexture2D* ImportedTexture = nullptr;
    FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools");
    FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");

    UTextureFactory* TextureFactory = NewObject<UTextureFactory>();
    TextureFactory->AddToRoot();
    TextureFactory->SuppressImportOverwriteDialog();

    UAssetImportTask* Task = NewObject<UAssetImportTask>();
    Task->AddToRoot();
    Task->bAutomated = true;
    Task->bReplaceExisting = true;
    Task->bSave = true;
    Task->DestinationPath = DestinationPath;
    Task->DestinationName = TextureName;
    Task->Filename = SourceFilePath;
    Task->Factory = TextureFactory;
    TextureFactory->SetAssetImportTask(Task);

    TArray<UAssetImportTask*> Tasks;
    Tasks.Add(Task);
    AssetToolsModule.Get().ImportAssetTasks(Tasks);

    for (const FString& ImportedObjectPath : Task->ImportedObjectPaths)
    {
        FAssetData AssetData = AssetRegistryModule.Get().GetAssetByObjectPath(FSoftObjectPath(ImportedObjectPath));
        UObject* ImportedAsset = AssetData.GetAsset();
        if (UTexture2D* CandidateTexture = Cast<UTexture2D>(ImportedAsset))
        {
            ImportedTexture = CandidateTexture;
            break;
        }
    }

    Task->RemoveFromRoot();
    TextureFactory->RemoveFromRoot();

    if (!ImportedTexture)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Failed to import texture from: %s"), *SourceFilePath));
    }

    // Rename if needed
    if (ImportedTexture->GetName() != TextureName)
    {
        FString PackagePath = FPaths::GetPath(ImportedTexture->GetOutermost()->GetName());
        TArray<FAssetRenameData> RenameData;
        RenameData.Add(FAssetRenameData(ImportedTexture, PackagePath, TextureName));
        AssetToolsModule.Get().RenameAssets(RenameData);
    }

    // Get the final asset path
    FString FinalAssetPath;
    if (ImportedTexture)
    {
        FinalAssetPath = ImportedTexture->GetPathName();
        int32 DotIndex;
        if (FinalAssetPath.FindChar('.', DotIndex))
        {
            FinalAssetPath = FinalAssetPath.Left(DotIndex);
        }
    }

    // Delete source file if requested
    if (bDeleteSource)
    {
        if (PlatformFile.DeleteFile(*SourceFilePath))
        {
            UE_LOG(LogTemp, Log, TEXT("Deleted source file: %s"), *SourceFilePath);
        }
        else
        {
            UE_LOG(LogTemp, Warning, TEXT("Failed to delete source file: %s"), *SourceFilePath);
        }
    }

    UE_LOG(LogTemp, Log, TEXT("Successfully imported texture: %s from %s"), *TextureName, *SourceFilePath);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("name"), TextureName);
    ResultObj->SetStringField(TEXT("path"), FinalAssetPath);
    ResultObj->SetStringField(TEXT("source_path"), SourceFilePath);
    ResultObj->SetBoolField(TEXT("deleted_source"), bDeleteSource);
    ResultObj->SetBoolField(TEXT("success"), true);

    return ResultObj;
}

// ============================================================================
// Material Properties
// ============================================================================

TSharedPtr<FJsonObject> FEpicUnrealMCPMaterialCommands::HandleSetMaterialProperties(const TSharedPtr<FJsonObject>& Params)
{
    FString MaterialName;
    if (!Params->TryGetStringField(TEXT("material_name"), MaterialName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'material_name' parameter"));
    }

    const FString MaterialPath = MaterialName.StartsWith(TEXT("/")) ? MaterialName : FString::Printf(TEXT("/Game/Materials/%s"), *MaterialName);
    UMaterial* Material = Cast<UMaterial>(UEditorAssetLibrary::LoadAsset(MaterialPath));
    UMaterialFunction* MaterialFunction = nullptr;
    UObject* GraphOwner = Material;
    if (!Material)
    {
        MaterialFunction = Cast<UMaterialFunction>(UEditorAssetLibrary::LoadAsset(MaterialPath));
        GraphOwner = MaterialFunction;
    }

    if (!GraphOwner)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Material or MaterialFunction not found: %s"), *MaterialPath));
    }

    TArray<FString> UpdatedProperties;

    // Shading Model
    FString ShadingModel;
    if (Params->TryGetStringField(TEXT("shading_model"), ShadingModel))
    {
        if (ShadingModel == TEXT("Unlit"))
            Material->SetShadingModel(EMaterialShadingModel::MSM_Unlit);
        else if (ShadingModel == TEXT("DefaultLit"))
            Material->SetShadingModel(EMaterialShadingModel::MSM_DefaultLit);
        else if (ShadingModel == TEXT("Subsurface"))
            Material->SetShadingModel(EMaterialShadingModel::MSM_Subsurface);
        else if (ShadingModel == TEXT("TwoSidedFoliage"))
            Material->SetShadingModel(EMaterialShadingModel::MSM_TwoSidedFoliage);
        UpdatedProperties.Add(TEXT("shading_model"));
    }

    // Blend Mode
    FString BlendMode;
    if (Params->TryGetStringField(TEXT("blend_mode"), BlendMode))
    {
        if (BlendMode == TEXT("Opaque"))
            Material->BlendMode = EBlendMode::BLEND_Opaque;
        else if (BlendMode == TEXT("Masked"))
            Material->BlendMode = EBlendMode::BLEND_Masked;
        else if (BlendMode == TEXT("Translucent"))
            Material->BlendMode = EBlendMode::BLEND_Translucent;
        else if (BlendMode == TEXT("Additive"))
            Material->BlendMode = EBlendMode::BLEND_Additive;
        UpdatedProperties.Add(TEXT("blend_mode"));
    }

    // Two Sided
    bool bTwoSided;
    if (Params->TryGetBoolField(TEXT("two_sided"), bTwoSided))
    {
        Material->TwoSided = bTwoSided ? 1 : 0;
        UpdatedProperties.Add(TEXT("two_sided"));
    }

    // Material Domain
    FString MaterialDomain;
    if (Params->TryGetStringField(TEXT("material_domain"), MaterialDomain))
    {
        if (MaterialDomain == TEXT("Surface"))
            Material->MaterialDomain = (EMaterialDomain)0;
        else if (MaterialDomain == TEXT("DeferredDecal"))
            Material->MaterialDomain = (EMaterialDomain)1;
        else if (MaterialDomain == TEXT("LightFunction"))
            Material->MaterialDomain = (EMaterialDomain)2;
        else if (MaterialDomain == TEXT("Volume"))
            Material->MaterialDomain = (EMaterialDomain)3;
        else if (MaterialDomain == TEXT("PostProcess"))
            Material->MaterialDomain = (EMaterialDomain)4;
        else if (MaterialDomain == TEXT("UserInterface") || MaterialDomain == TEXT("UI"))
            Material->MaterialDomain = (EMaterialDomain)5;
        UpdatedProperties.Add(TEXT("material_domain"));
    }

    Material->MarkPackageDirty();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetArrayField(TEXT("updated_properties"), 
        TArray<TSharedPtr<FJsonValue>>());
    ResultObj->SetBoolField(TEXT("success"), true);

    return ResultObj;
}

// ============================================================================
// Helper Functions
// ============================================================================

UMaterialExpression* FEpicUnrealMCPMaterialCommands::FindMaterialExpressionById(UMaterial* Material, const FString& NodeId)
{
    if (!Material || NodeId.IsEmpty()) return nullptr;

    TArray<FString> Parts;
    NodeId.ParseIntoArray(Parts, TEXT("_"), false);
    
    if (Parts.Num() >= 3)
    {
        int32 UniqueId = FCString::Atoi(*Parts.Last());
        
        const TArray<UMaterialExpression*>& Expressions = Material->GetExpressionCollection().Expressions;
        for (UMaterialExpression* Expr : Expressions)
        {
            if (Expr && Expr->GetUniqueID() == UniqueId)
            {
                return Expr;
            }
        }
    }

    return nullptr;
}

FExpressionInput* FEpicUnrealMCPMaterialCommands::GetExpressionInputByName(UMaterialExpression* Expression, const FString& InputName)
{
    if (!Expression || InputName.IsEmpty()) return nullptr;

    FString LowerInputName = InputName.ToLower();
    
    int32 InputIndex = 0;
    FExpressionInput* Input = Expression->GetInput(InputIndex);
    while (Input)
    {
        FString Name = Expression->GetInputName(InputIndex).ToString().ToLower();
        if (Name == LowerInputName)
        {
            return Input;
        }
        InputIndex++;
        Input = Expression->GetInput(InputIndex);
    }

    // Handle common cases directly
    if (UMaterialExpressionMultiply* Multiply = Cast<UMaterialExpressionMultiply>(Expression))
    {
        if (LowerInputName == TEXT("a")) return &Multiply->A;
        if (LowerInputName == TEXT("b")) return &Multiply->B;
    }
    else if (UMaterialExpressionAdd* Add = Cast<UMaterialExpressionAdd>(Expression))
    {
        if (LowerInputName == TEXT("a")) return &Add->A;
        if (LowerInputName == TEXT("b")) return &Add->B;
    }
    else if (UMaterialExpressionSubtract* Sub = Cast<UMaterialExpressionSubtract>(Expression))
    {
        if (LowerInputName == TEXT("a")) return &Sub->A;
        if (LowerInputName == TEXT("b")) return &Sub->B;
    }
    else if (UMaterialExpressionDivide* Div = Cast<UMaterialExpressionDivide>(Expression))
    {
        if (LowerInputName == TEXT("a")) return &Div->A;
        if (LowerInputName == TEXT("b")) return &Div->B;
    }
    else if (UMaterialExpressionLinearInterpolate* Lerp = Cast<UMaterialExpressionLinearInterpolate>(Expression))
    {
        if (LowerInputName == TEXT("a")) return &Lerp->A;
        if (LowerInputName == TEXT("b")) return &Lerp->B;
        if (LowerInputName == TEXT("alpha")) return &Lerp->Alpha;
    }
    else if (UMaterialExpressionClamp* Clamp = Cast<UMaterialExpressionClamp>(Expression))
    {
        if (LowerInputName == TEXT("input")) return &Clamp->Input;
    }
    else if (UMaterialExpressionPanner* Panner = Cast<UMaterialExpressionPanner>(Expression))
    {
        if (LowerInputName == TEXT("coordinate")) return &Panner->Coordinate;
        if (LowerInputName == TEXT("time")) return &Panner->Time;
    }
    else if (UMaterialExpressionRotator* Rotator = Cast<UMaterialExpressionRotator>(Expression))
    {
        if (LowerInputName == TEXT("coordinate")) return &Rotator->Coordinate;
        if (LowerInputName == TEXT("time")) return &Rotator->Time;
    }
    else if (UMaterialExpressionPower* Power = Cast<UMaterialExpressionPower>(Expression))
    {
        if (LowerInputName == TEXT("base")) return &Power->Base;
        if (LowerInputName == TEXT("exponent")) return &Power->Exponent;
    }
    else if (UMaterialExpressionTextureSample* TexSample = Cast<UMaterialExpressionTextureSample>(Expression))
    {
        if (LowerInputName == TEXT("coordinates")) return &TexSample->Coordinates;
    }
    else if (UMaterialExpressionFunctionOutput* FunctionOutput = Cast<UMaterialExpressionFunctionOutput>(Expression))
    {
        if (LowerInputName == TEXT("input") || LowerInputName == TEXT("a")) return &FunctionOutput->A;
    }
    else if (UMaterialExpressionMaterialFunctionCall* FunctionCall = Cast<UMaterialExpressionMaterialFunctionCall>(Expression))
    {
        for (int32 FuncInputIdx = 0; FuncInputIdx < FunctionCall->FunctionInputs.Num(); ++FuncInputIdx)
        {
            FFunctionExpressionInput& FuncInput = FunctionCall->FunctionInputs[FuncInputIdx];
            const FString FuncInputName = FuncInput.ExpressionInput
                ? FuncInput.ExpressionInput->InputName.ToString().ToLower()
                : Expression->GetInputName(FuncInputIdx).ToString().ToLower();
            if (!FuncInputName.IsEmpty() && FuncInputName == LowerInputName)
            {
                return &FuncInput.Input;
            }
        }
    }

    return nullptr;
}

int32 FEpicUnrealMCPMaterialCommands::GetExpressionOutputIndexByName(UMaterialExpression* Expression, const FString& OutputName)
{
    if (!Expression)
    {
        return 0;
    }

    if (OutputName.IsEmpty())
    {
        return 0;
    }

    const int32 ExplicitIndex = ParseExplicitOutputIndex(OutputName);
    if (ExplicitIndex != INDEX_NONE)
    {
        return ExplicitIndex;
    }

    const FString LowerOutputName = OutputName.ToLower();
    if (LowerOutputName == TEXT("output") || LowerOutputName == TEXT("rgb") || LowerOutputName == TEXT("rgba"))
    {
        return 0;
    }

    TArray<FExpressionOutput>& Outputs = Expression->GetOutputs();
    for (int32 OutputIndex = 0; OutputIndex < Outputs.Num(); ++OutputIndex)
    {
        const FString CurrentName = Outputs[OutputIndex].OutputName.ToString().ToLower();
        if (!CurrentName.IsEmpty() && CurrentName == LowerOutputName)
        {
            return OutputIndex;
        }
    }

    if (Cast<UMaterialExpressionTextureSample>(Expression) || Cast<UMaterialExpressionTextureSampleParameter2D>(Expression))
    {
        if (LowerOutputName == TEXT("r") || LowerOutputName == TEXT("red"))
        {
            return 1;
        }
        if (LowerOutputName == TEXT("g") || LowerOutputName == TEXT("green"))
        {
            return 2;
        }
        if (LowerOutputName == TEXT("b") || LowerOutputName == TEXT("blue"))
        {
            return 3;
        }
        if (LowerOutputName == TEXT("a") || LowerOutputName == TEXT("alpha"))
        {
            return 4;
        }
    }

    return 0;
}

FExpressionInput* FEpicUnrealMCPMaterialCommands::GetMaterialPropertyInput(UMaterial* Material, const FString& PropertyName)
{
    if (!Material || PropertyName.IsEmpty()) return nullptr;

    FString LowerPropName = PropertyName.ToLower();

    EMaterialProperty MaterialProperty = MP_MAX;

    if (LowerPropName == TEXT("basecolor") || LowerPropName == TEXT("base_color"))
        MaterialProperty = MP_BaseColor;
    else if (LowerPropName == TEXT("metallic"))
        MaterialProperty = MP_Metallic;
    else if (LowerPropName == TEXT("specular"))
        MaterialProperty = MP_Specular;
    else if (LowerPropName == TEXT("roughness"))
        MaterialProperty = MP_Roughness;
    else if (LowerPropName == TEXT("normal"))
        MaterialProperty = MP_Normal;
    else if (LowerPropName == TEXT("worldpositionoffset") || LowerPropName == TEXT("world_position_offset"))
        MaterialProperty = MP_WorldPositionOffset;
    else if (LowerPropName == TEXT("emissivecolor") || LowerPropName == TEXT("emissive_color"))
        MaterialProperty = MP_EmissiveColor;
    else if (LowerPropName == TEXT("opacity"))
        MaterialProperty = MP_Opacity;
    else if (LowerPropName == TEXT("opacitymask") || LowerPropName == TEXT("opacity_mask"))
        MaterialProperty = MP_OpacityMask;
    else if (LowerPropName == TEXT("ambientocclusion") || LowerPropName == TEXT("ambient_occlusion"))
        MaterialProperty = MP_AmbientOcclusion;
    else if (LowerPropName == TEXT("refraction"))
        MaterialProperty = MP_Refraction;
    else if (LowerPropName == TEXT("pixeldepthoffset") || LowerPropName == TEXT("pixel_depth_offset"))
        MaterialProperty = MP_PixelDepthOffset;
    else if (LowerPropName == TEXT("subsurfacecolor") || LowerPropName == TEXT("subsurface_color"))
        MaterialProperty = MP_SubsurfaceColor;
    else
        return nullptr;

    return Material->GetExpressionInputForProperty(MaterialProperty);
}

// ============================================================================
// Get Material Graph
// ============================================================================

TSharedPtr<FJsonObject> FEpicUnrealMCPMaterialCommands::HandleGetMaterialGraph(const TSharedPtr<FJsonObject>& Params)
{
    // Support both material_name (for backward compatibility) and asset_path
    FString AssetPath;
    if (!Params->TryGetStringField(TEXT("asset_path"), AssetPath))
    {
        if (!Params->TryGetStringField(TEXT("material_name"), AssetPath))
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'asset_path' or 'material_name' parameter"));
        }
    }

    // Build full path if not already a full path
    FString FullPath = AssetPath.StartsWith(TEXT("/")) ? AssetPath : FString::Printf(TEXT("/Game/Materials/%s"), *AssetPath);
    
    // Try to load as Material first, then as MaterialFunction
    UMaterial* Material = Cast<UMaterial>(UEditorAssetLibrary::LoadAsset(FullPath));
    UMaterialFunction* MaterialFunction = nullptr;
    
    if (!Material)
    {
        MaterialFunction = Cast<UMaterialFunction>(UEditorAssetLibrary::LoadAsset(FullPath));
        if (!MaterialFunction)
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Asset not found or not a Material/MaterialFunction: %s"), *FullPath));
        }
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    
    // Set common fields based on asset type
    if (Material)
    {
        ResultObj->SetStringField(TEXT("asset_type"), TEXT("Material"));
        ResultObj->SetStringField(TEXT("name"), Material->GetName());
        ResultObj->SetStringField(TEXT("path"), FullPath);
    }
    else if (MaterialFunction)
    {
        ResultObj->SetStringField(TEXT("asset_type"), TEXT("MaterialFunction"));
        ResultObj->SetStringField(TEXT("name"), MaterialFunction->GetName());
        ResultObj->SetStringField(TEXT("path"), FullPath);
        ResultObj->SetStringField(TEXT("description"), MaterialFunction->Description);
    }
    
    // Get expressions reference based on asset type
    const TArray<UMaterialExpression*>& Expressions = Material 
        ? Material->GetExpressionCollection().Expressions 
        : MaterialFunction->GetExpressionCollection().Expressions;
    
    // For MaterialFunction: collect inputs and outputs
    TArray<TSharedPtr<FJsonValue>> InputsArray;
    TArray<TSharedPtr<FJsonValue>> OutputsArray;
    
    if (MaterialFunction)
    {
        for (UMaterialExpression* Expr : Expressions)
        {
            if (!Expr) continue;
            
            if (UMaterialExpressionFunctionInput* InputExpr = Cast<UMaterialExpressionFunctionInput>(Expr))
            {
                TSharedPtr<FJsonObject> InputObj = MakeShared<FJsonObject>();
                InputObj->SetStringField(TEXT("name"), InputExpr->InputName.ToString());
                InputObj->SetStringField(TEXT("description"), InputExpr->Description);
                InputObj->SetStringField(TEXT("id"), InputExpr->Id.ToString());
                
                FString InputType;
                switch (InputExpr->InputType)
                {
                    case FunctionInput_Vector2: InputType = TEXT("Vector2"); break;
                    case FunctionInput_Vector3: InputType = TEXT("Vector3"); break;
                    case FunctionInput_Vector4: InputType = TEXT("Vector4"); break;
                    case FunctionInput_Scalar: InputType = TEXT("Scalar"); break;
                    case FunctionInput_Bool: InputType = TEXT("Bool"); break;
                    default: InputType = TEXT("Unknown"); break;
                }
                InputObj->SetStringField(TEXT("type"), InputType);
                
                InputsArray.Add(MakeShared<FJsonValueObject>(InputObj));
            }
            else if (UMaterialExpressionFunctionOutput* OutputExpr = Cast<UMaterialExpressionFunctionOutput>(Expr))
            {
                TSharedPtr<FJsonObject> OutputObj = MakeShared<FJsonObject>();
                OutputObj->SetStringField(TEXT("name"), OutputExpr->OutputName.ToString());
                OutputObj->SetStringField(TEXT("description"), OutputExpr->Description);
                OutputObj->SetStringField(TEXT("id"), OutputExpr->Id.ToString());
                OutputsArray.Add(MakeShared<FJsonValueObject>(OutputObj));
            }
        }
        
        ResultObj->SetArrayField(TEXT("inputs"), InputsArray);
        ResultObj->SetArrayField(TEXT("outputs"), OutputsArray);
    }
    
    // Build nodes array with detailed type-specific information
    TArray<TSharedPtr<FJsonValue>> NodesArray;
    TMap<UMaterialExpression*, FString> ExprToNodeId;
    
    for (UMaterialExpression* Expr : Expressions)
    {
        if (!Expr) continue;
        
        TSharedPtr<FJsonObject> NodeObj = MakeShared<FJsonObject>();
        
        // Get expression type
        FString ExprType = Expr->GetClass()->GetName();
        if (ExprType.StartsWith(TEXT("MaterialExpression")))
        {
            ExprType = ExprType.Mid(18);
        }
        
        FString NodeId = FString::Printf(TEXT("Expr_%s_%d"), *ExprType, Expr->GetUniqueID());
        ExprToNodeId.Add(Expr, NodeId);
        
        NodeObj->SetStringField(TEXT("node_id"), NodeId);
        NodeObj->SetStringField(TEXT("type"), ExprType);
        NodeObj->SetStringField(TEXT("name"), Expr->GetName());
        NodeObj->SetNumberField(TEXT("pos_x"), Expr->MaterialExpressionEditorX);
        NodeObj->SetNumberField(TEXT("pos_y"), Expr->MaterialExpressionEditorY);
        
        if (!Expr->Desc.IsEmpty())
        {
            NodeObj->SetStringField(TEXT("desc"), Expr->Desc);
        }
        
        // Add type-specific information
        if (UMaterialExpressionFunctionInput* InputExpr = Cast<UMaterialExpressionFunctionInput>(Expr))
        {
            NodeObj->SetStringField(TEXT("input_name"), InputExpr->InputName.ToString());
            NodeObj->SetStringField(TEXT("input_id"), InputExpr->Id.ToString());
            NodeObj->SetStringField(TEXT("description"), InputExpr->Description);
        }
        else if (UMaterialExpressionFunctionOutput* OutputExpr = Cast<UMaterialExpressionFunctionOutput>(Expr))
        {
            NodeObj->SetStringField(TEXT("output_name"), OutputExpr->OutputName.ToString());
            NodeObj->SetStringField(TEXT("output_id"), OutputExpr->Id.ToString());
            NodeObj->SetStringField(TEXT("description"), OutputExpr->Description);
        }
        else if (UMaterialExpressionScalarParameter* ScalarParam = Cast<UMaterialExpressionScalarParameter>(Expr))
        {
            NodeObj->SetStringField(TEXT("parameter_name"), ScalarParam->ParameterName.ToString());
            NodeObj->SetNumberField(TEXT("default_value"), ScalarParam->DefaultValue);
        }
        else if (UMaterialExpressionVectorParameter* VectorParam = Cast<UMaterialExpressionVectorParameter>(Expr))
        {
            NodeObj->SetStringField(TEXT("parameter_name"), VectorParam->ParameterName.ToString());
            TArray<TSharedPtr<FJsonValue>> DefaultValue;
            DefaultValue.Add(MakeShared<FJsonValueNumber>(VectorParam->DefaultValue.R));
            DefaultValue.Add(MakeShared<FJsonValueNumber>(VectorParam->DefaultValue.G));
            DefaultValue.Add(MakeShared<FJsonValueNumber>(VectorParam->DefaultValue.B));
            DefaultValue.Add(MakeShared<FJsonValueNumber>(VectorParam->DefaultValue.A));
            NodeObj->SetArrayField(TEXT("default_value"), DefaultValue);
        }
        else if (UMaterialExpressionConstant* ConstExpr = Cast<UMaterialExpressionConstant>(Expr))
        {
            NodeObj->SetNumberField(TEXT("value"), ConstExpr->R);
        }
        else if (UMaterialExpressionConstant2Vector* Const2Expr = Cast<UMaterialExpressionConstant2Vector>(Expr))
        {
            TArray<TSharedPtr<FJsonValue>> ValueArray;
            ValueArray.Add(MakeShared<FJsonValueNumber>(Const2Expr->R));
            ValueArray.Add(MakeShared<FJsonValueNumber>(Const2Expr->G));
            NodeObj->SetArrayField(TEXT("value"), ValueArray);
        }
        else if (UMaterialExpressionConstant3Vector* Const3Expr = Cast<UMaterialExpressionConstant3Vector>(Expr))
        {
            TArray<TSharedPtr<FJsonValue>> ValueArray;
            ValueArray.Add(MakeShared<FJsonValueNumber>(Const3Expr->Constant.R));
            ValueArray.Add(MakeShared<FJsonValueNumber>(Const3Expr->Constant.G));
            ValueArray.Add(MakeShared<FJsonValueNumber>(Const3Expr->Constant.B));
            NodeObj->SetArrayField(TEXT("value"), ValueArray);
        }
        else if (UMaterialExpressionConstant4Vector* Const4Expr = Cast<UMaterialExpressionConstant4Vector>(Expr))
        {
            TArray<TSharedPtr<FJsonValue>> ValueArray;
            ValueArray.Add(MakeShared<FJsonValueNumber>(Const4Expr->Constant.R));
            ValueArray.Add(MakeShared<FJsonValueNumber>(Const4Expr->Constant.G));
            ValueArray.Add(MakeShared<FJsonValueNumber>(Const4Expr->Constant.B));
            ValueArray.Add(MakeShared<FJsonValueNumber>(Const4Expr->Constant.A));
            NodeObj->SetArrayField(TEXT("value"), ValueArray);
        }
        else if (UMaterialExpressionTextureObject* TexObj = Cast<UMaterialExpressionTextureObject>(Expr))
        {
            if (TexObj->Texture)
            {
                NodeObj->SetStringField(TEXT("texture_path"), TexObj->Texture->GetPathName());
            }
        }
        else if (UMaterialExpressionTextureSampleParameter2D* TexParam = Cast<UMaterialExpressionTextureSampleParameter2D>(Expr))
        {
            if (TexParam->Texture)
            {
                NodeObj->SetStringField(TEXT("texture_path"), TexParam->Texture->GetPathName());
            }
            NodeObj->SetStringField(TEXT("sampler_type"), SamplerTypeToString(TexParam->SamplerType));
            NodeObj->SetStringField(TEXT("parameter_name"), TexParam->ParameterName.ToString());
        }
        else if (UMaterialExpressionTextureSample* TexSample = Cast<UMaterialExpressionTextureSample>(Expr))
        {
            if (TexSample->Texture)
            {
                NodeObj->SetStringField(TEXT("texture_path"), TexSample->Texture->GetPathName());
            }
            NodeObj->SetStringField(TEXT("sampler_type"), SamplerTypeToString(TexSample->SamplerType));
        }
        else if (UMaterialExpressionCustom* CustomExpr = Cast<UMaterialExpressionCustom>(Expr))
        {
            NodeObj->SetStringField(TEXT("code"), CustomExpr->Code);
            NodeObj->SetStringField(TEXT("output_type"), 
                CustomExpr->OutputType == ECustomMaterialOutputType::CMOT_Float1 ? TEXT("Float1") :
                CustomExpr->OutputType == ECustomMaterialOutputType::CMOT_Float2 ? TEXT("Float2") :
                CustomExpr->OutputType == ECustomMaterialOutputType::CMOT_Float3 ? TEXT("Float3") :
                CustomExpr->OutputType == ECustomMaterialOutputType::CMOT_Float4 ? TEXT("Float4") : TEXT("Unknown"));
            
            TArray<TSharedPtr<FJsonValue>> CustomInputs;
            for (const FCustomInput& CustomInput : CustomExpr->Inputs)
            {
                if (CustomInput.InputName.IsNone())
                {
                    continue;
                }

                TSharedPtr<FJsonObject> CustomInputObj = MakeShared<FJsonObject>();
                CustomInputObj->SetStringField(TEXT("input_name"), CustomInput.InputName.ToString());
                CustomInputs.Add(MakeShared<FJsonValueObject>(CustomInputObj));
            }
            NodeObj->SetArrayField(TEXT("inputs"), CustomInputs);
        }
        
        NodesArray.Add(MakeShared<FJsonValueObject>(NodeObj));
    }
    
    // Build connections array with named inputs
    TArray<TSharedPtr<FJsonValue>> ConnectionsArray;
    
    for (UMaterialExpression* Expr : Expressions)
    {
        if (!Expr) continue;
        
        FString TargetNodeId = ExprToNodeId[Expr];
        
        // Lambda for adding named connections
        auto AddConnection = [&](UMaterialExpression* SourceExpr, const FString& OutputName, const FString& InputName)
        {
            if (SourceExpr)
            {
                FString* FromNodeId = ExprToNodeId.Find(SourceExpr);
                if (FromNodeId)
                {
                    TSharedPtr<FJsonObject> ConnObj = MakeShared<FJsonObject>();
                    ConnObj->SetStringField(TEXT("from"), *FromNodeId);
                    ConnObj->SetStringField(TEXT("to"), TargetNodeId);
                    ConnObj->SetStringField(TEXT("from_output"), OutputName);
                    ConnObj->SetStringField(TEXT("to_input"), InputName);
                    ConnectionsArray.Add(MakeShared<FJsonValueObject>(ConnObj));
                }
            }
        };
        
        // Handle specific expression types with named inputs
        if (UMaterialExpressionMultiply* Multiply = Cast<UMaterialExpressionMultiply>(Expr))
        {
            if (Multiply->A.Expression) AddConnection(Multiply->A.Expression, FString::Printf(TEXT("Output_%d"), Multiply->A.OutputIndex), TEXT("A"));
            if (Multiply->B.Expression) AddConnection(Multiply->B.Expression, FString::Printf(TEXT("Output_%d"), Multiply->B.OutputIndex), TEXT("B"));
        }
        else if (UMaterialExpressionAdd* Add = Cast<UMaterialExpressionAdd>(Expr))
        {
            if (Add->A.Expression) AddConnection(Add->A.Expression, FString::Printf(TEXT("Output_%d"), Add->A.OutputIndex), TEXT("A"));
            if (Add->B.Expression) AddConnection(Add->B.Expression, FString::Printf(TEXT("Output_%d"), Add->B.OutputIndex), TEXT("B"));
        }
        else if (UMaterialExpressionSubtract* Sub = Cast<UMaterialExpressionSubtract>(Expr))
        {
            if (Sub->A.Expression) AddConnection(Sub->A.Expression, FString::Printf(TEXT("Output_%d"), Sub->A.OutputIndex), TEXT("A"));
            if (Sub->B.Expression) AddConnection(Sub->B.Expression, FString::Printf(TEXT("Output_%d"), Sub->B.OutputIndex), TEXT("B"));
        }
        else if (UMaterialExpressionDivide* Div = Cast<UMaterialExpressionDivide>(Expr))
        {
            if (Div->A.Expression) AddConnection(Div->A.Expression, FString::Printf(TEXT("Output_%d"), Div->A.OutputIndex), TEXT("A"));
            if (Div->B.Expression) AddConnection(Div->B.Expression, FString::Printf(TEXT("Output_%d"), Div->B.OutputIndex), TEXT("B"));
        }
        else if (UMaterialExpressionLinearInterpolate* Lerp = Cast<UMaterialExpressionLinearInterpolate>(Expr))
        {
            if (Lerp->A.Expression) AddConnection(Lerp->A.Expression, FString::Printf(TEXT("Output_%d"), Lerp->A.OutputIndex), TEXT("A"));
            if (Lerp->B.Expression) AddConnection(Lerp->B.Expression, FString::Printf(TEXT("Output_%d"), Lerp->B.OutputIndex), TEXT("B"));
            if (Lerp->Alpha.Expression) AddConnection(Lerp->Alpha.Expression, FString::Printf(TEXT("Output_%d"), Lerp->Alpha.OutputIndex), TEXT("Alpha"));
        }
        else if (UMaterialExpressionTextureSample* TexSample = Cast<UMaterialExpressionTextureSample>(Expr))
        {
            if (TexSample->Coordinates.Expression) AddConnection(TexSample->Coordinates.Expression, FString::Printf(TEXT("Output_%d"), TexSample->Coordinates.OutputIndex), TEXT("Coordinates"));
        }
        else if (UMaterialExpressionFunctionOutput* FuncOutput = Cast<UMaterialExpressionFunctionOutput>(Expr))
        {
            if (FuncOutput->A.Expression) AddConnection(FuncOutput->A.Expression, FString::Printf(TEXT("Output_%d"), FuncOutput->A.OutputIndex), TEXT("Input"));
        }
        else if (UMaterialExpressionComponentMask* Mask = Cast<UMaterialExpressionComponentMask>(Expr))
        {
            if (Mask->Input.Expression) AddConnection(Mask->Input.Expression, FString::Printf(TEXT("Output_%d"), Mask->Input.OutputIndex), TEXT("Input"));
        }
        else if (UMaterialExpressionOneMinus* OneMinus = Cast<UMaterialExpressionOneMinus>(Expr))
        {
            if (OneMinus->Input.Expression) AddConnection(OneMinus->Input.Expression, FString::Printf(TEXT("Output_%d"), OneMinus->Input.OutputIndex), TEXT("Input"));
        }
        else if (UMaterialExpressionSaturate* Saturate = Cast<UMaterialExpressionSaturate>(Expr))
        {
            if (Saturate->Input.Expression) AddConnection(Saturate->Input.Expression, FString::Printf(TEXT("Output_%d"), Saturate->Input.OutputIndex), TEXT("Input"));
        }
        else if (UMaterialExpressionAbs* AbsExpr = Cast<UMaterialExpressionAbs>(Expr))
        {
            if (AbsExpr->Input.Expression) AddConnection(AbsExpr->Input.Expression, FString::Printf(TEXT("Output_%d"), AbsExpr->Input.OutputIndex), TEXT("Input"));
        }
        else if (UMaterialExpressionCeil* Ceil = Cast<UMaterialExpressionCeil>(Expr))
        {
            if (Ceil->Input.Expression) AddConnection(Ceil->Input.Expression, FString::Printf(TEXT("Output_%d"), Ceil->Input.OutputIndex), TEXT("Input"));
        }
        else if (UMaterialExpressionFloor* Floor = Cast<UMaterialExpressionFloor>(Expr))
        {
            if (Floor->Input.Expression) AddConnection(Floor->Input.Expression, FString::Printf(TEXT("Output_%d"), Floor->Input.OutputIndex), TEXT("Input"));
        }
        else if (UMaterialExpressionFrac* Frac = Cast<UMaterialExpressionFrac>(Expr))
        {
            if (Frac->Input.Expression) AddConnection(Frac->Input.Expression, FString::Printf(TEXT("Output_%d"), Frac->Input.OutputIndex), TEXT("Input"));
        }
        else if (UMaterialExpressionSine* Sine = Cast<UMaterialExpressionSine>(Expr))
        {
            if (Sine->Input.Expression) AddConnection(Sine->Input.Expression, FString::Printf(TEXT("Output_%d"), Sine->Input.OutputIndex), TEXT("Input"));
        }
        else if (UMaterialExpressionCosine* Cosine = Cast<UMaterialExpressionCosine>(Expr))
        {
            if (Cosine->Input.Expression) AddConnection(Cosine->Input.Expression, FString::Printf(TEXT("Output_%d"), Cosine->Input.OutputIndex), TEXT("Input"));
        }
        else if (UMaterialExpressionPower* Power = Cast<UMaterialExpressionPower>(Expr))
        {
            if (Power->Base.Expression) AddConnection(Power->Base.Expression, FString::Printf(TEXT("Output_%d"), Power->Base.OutputIndex), TEXT("Base"));
            if (Power->Exponent.Expression) AddConnection(Power->Exponent.Expression, FString::Printf(TEXT("Output_%d"), Power->Exponent.OutputIndex), TEXT("Exponent"));
        }
        else if (UMaterialExpressionDotProduct* DotProd = Cast<UMaterialExpressionDotProduct>(Expr))
        {
            if (DotProd->A.Expression) AddConnection(DotProd->A.Expression, FString::Printf(TEXT("Output_%d"), DotProd->A.OutputIndex), TEXT("A"));
            if (DotProd->B.Expression) AddConnection(DotProd->B.Expression, FString::Printf(TEXT("Output_%d"), DotProd->B.OutputIndex), TEXT("B"));
        }
        else if (UMaterialExpressionCrossProduct* CrossProd = Cast<UMaterialExpressionCrossProduct>(Expr))
        {
            if (CrossProd->A.Expression) AddConnection(CrossProd->A.Expression, FString::Printf(TEXT("Output_%d"), CrossProd->A.OutputIndex), TEXT("A"));
            if (CrossProd->B.Expression) AddConnection(CrossProd->B.Expression, FString::Printf(TEXT("Output_%d"), CrossProd->B.OutputIndex), TEXT("B"));
        }
        else if (UMaterialExpressionNormalize* Normalize = Cast<UMaterialExpressionNormalize>(Expr))
        {
            if (Normalize->VectorInput.Expression) AddConnection(Normalize->VectorInput.Expression, FString::Printf(TEXT("Output_%d"), Normalize->VectorInput.OutputIndex), TEXT("VectorInput"));
        }
        else if (UMaterialExpressionAppendVector* Append = Cast<UMaterialExpressionAppendVector>(Expr))
        {
            if (Append->A.Expression) AddConnection(Append->A.Expression, FString::Printf(TEXT("Output_%d"), Append->A.OutputIndex), TEXT("A"));
            if (Append->B.Expression) AddConnection(Append->B.Expression, FString::Printf(TEXT("Output_%d"), Append->B.OutputIndex), TEXT("B"));
        }
        else if (UMaterialExpressionPanner* Panner = Cast<UMaterialExpressionPanner>(Expr))
        {
            if (Panner->Coordinate.Expression) AddConnection(Panner->Coordinate.Expression, FString::Printf(TEXT("Output_%d"), Panner->Coordinate.OutputIndex), TEXT("Coordinate"));
            if (Panner->Time.Expression) AddConnection(Panner->Time.Expression, FString::Printf(TEXT("Output_%d"), Panner->Time.OutputIndex), TEXT("Time"));
        }
        else if (UMaterialExpressionRotator* Rotator = Cast<UMaterialExpressionRotator>(Expr))
        {
            if (Rotator->Coordinate.Expression) AddConnection(Rotator->Coordinate.Expression, FString::Printf(TEXT("Output_%d"), Rotator->Coordinate.OutputIndex), TEXT("Coordinate"));
            if (Rotator->Time.Expression) AddConnection(Rotator->Time.Expression, FString::Printf(TEXT("Output_%d"), Rotator->Time.OutputIndex), TEXT("Time"));
        }
        else if (UMaterialExpressionDesaturation* Desat = Cast<UMaterialExpressionDesaturation>(Expr))
        {
            if (Desat->Input.Expression) AddConnection(Desat->Input.Expression, FString::Printf(TEXT("Output_%d"), Desat->Input.OutputIndex), TEXT("Input"));
            if (Desat->Fraction.Expression) AddConnection(Desat->Fraction.Expression, FString::Printf(TEXT("Output_%d"), Desat->Fraction.OutputIndex), TEXT("Fraction"));
        }
        else if (UMaterialExpressionClamp* ClampExpr = Cast<UMaterialExpressionClamp>(Expr))
        {
            if (ClampExpr->Input.Expression) AddConnection(ClampExpr->Input.Expression, FString::Printf(TEXT("Output_%d"), ClampExpr->Input.OutputIndex), TEXT("Input"));
        }
        else if (UMaterialExpressionMaterialFunctionCall* FuncCall = Cast<UMaterialExpressionMaterialFunctionCall>(Expr))
        {
            for (int32 FuncInputIdx = 0; FuncInputIdx < FuncCall->FunctionInputs.Num(); FuncInputIdx++)
            {
                const FFunctionExpressionInput& FuncInput = FuncCall->FunctionInputs[FuncInputIdx];
                if (FuncInput.Input.Expression)
                {
                    FString InputName = FuncInput.ExpressionInput ? FuncInput.ExpressionInput->InputName.ToString() : FString::Printf(TEXT("Input_%d"), FuncInputIdx);
                    AddConnection(FuncInput.Input.Expression, FString::Printf(TEXT("Output_%d"), FuncInput.Input.OutputIndex), InputName);
                }
            }
        }
        else
        {
            // Generic input iteration for other expression types
            int32 InputIndex = 0;
            FExpressionInput* Input = Expr->GetInput(InputIndex);
            while (Input)
            {
                if (Input->Expression)
                {
                    FString* SourceNodeId = ExprToNodeId.Find(Input->Expression);
                    if (SourceNodeId)
                    {
                        TSharedPtr<FJsonObject> ConnObj = MakeShared<FJsonObject>();
                        ConnObj->SetStringField(TEXT("from"), *SourceNodeId);
                        ConnObj->SetStringField(TEXT("to"), TargetNodeId);
                        ConnObj->SetStringField(TEXT("from_output"), FString::Printf(TEXT("Output_%d"), Input->OutputIndex));
                        ConnObj->SetStringField(TEXT("to_input"), FString::Printf(TEXT("Input_%d"), InputIndex));
                        ConnectionsArray.Add(MakeShared<FJsonValueObject>(ConnObj));
                    }
                }
                InputIndex++;
                Input = Expr->GetInput(InputIndex);
            }
        }
    }
    
    // For Material: add property connections
    if (Material)
    {
        TSharedPtr<FJsonObject> PropertyConnectionsObj = MakeShared<FJsonObject>();
        
        auto AddPropertyConnection = [&](const FString& PropertyName, EMaterialProperty MaterialProperty) {
            FExpressionInput* PropertyInput = Material->GetExpressionInputForProperty(MaterialProperty);
            if (PropertyInput && PropertyInput->Expression)
            {
                TSharedPtr<FJsonObject> PropConnObj = MakeShared<FJsonObject>();
                FString* ConnectedNodeId = ExprToNodeId.Find(PropertyInput->Expression);
                if (ConnectedNodeId)
                {
                    PropConnObj->SetStringField(TEXT("node_id"), *ConnectedNodeId);
                    PropConnObj->SetNumberField(TEXT("output_index"), PropertyInput->OutputIndex);
                    PropertyConnectionsObj->SetObjectField(PropertyName, PropConnObj);
                }
            }
        };
        
        AddPropertyConnection(TEXT("BaseColor"), MP_BaseColor);
        AddPropertyConnection(TEXT("Metallic"), MP_Metallic);
        AddPropertyConnection(TEXT("Specular"), MP_Specular);
        AddPropertyConnection(TEXT("Roughness"), MP_Roughness);
        AddPropertyConnection(TEXT("Normal"), MP_Normal);
        AddPropertyConnection(TEXT("EmissiveColor"), MP_EmissiveColor);
        AddPropertyConnection(TEXT("Opacity"), MP_Opacity);
        AddPropertyConnection(TEXT("OpacityMask"), MP_OpacityMask);
        AddPropertyConnection(TEXT("AmbientOcclusion"), MP_AmbientOcclusion);
        
        ResultObj->SetObjectField(TEXT("property_connections"), PropertyConnectionsObj);
    }
    
    ResultObj->SetArrayField(TEXT("nodes"), NodesArray);
    ResultObj->SetArrayField(TEXT("connections"), ConnectionsArray);
    ResultObj->SetNumberField(TEXT("node_count"), NodesArray.Num());
    ResultObj->SetNumberField(TEXT("connection_count"), ConnectionsArray.Num());
    ResultObj->SetBoolField(TEXT("success"), true);
    
    return ResultObj;
}

// ============================================================================
// Build Material Graph
// ============================================================================

TSharedPtr<FJsonObject> FEpicUnrealMCPMaterialCommands::HandleBuildMaterialGraph(const TSharedPtr<FJsonObject>& Params)
{
    // Get material name
    FString MaterialName;
    if (!Params->TryGetStringField(TEXT("material_name"), MaterialName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'material_name' parameter"));
    }

    // Find or load the material / material function
    FString MaterialPath = MaterialName.StartsWith(TEXT("/")) ? MaterialName : FString::Printf(TEXT("/Game/Materials/%s"), *MaterialName);
    UMaterial* Material = Cast<UMaterial>(UEditorAssetLibrary::LoadAsset(MaterialPath));
    UMaterialFunction* MaterialFunction = nullptr;
    UObject* GraphOwner = Material;
    if (!Material)
    {
        MaterialFunction = Cast<UMaterialFunction>(UEditorAssetLibrary::LoadAsset(MaterialPath));
        GraphOwner = MaterialFunction;
    }

    if (!GraphOwner)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Material or MaterialFunction not found: %s"), *MaterialPath));
    }

    // Track created nodes for connection mapping
    TMap<FString, UMaterialExpression*> NodeIdToExpression;
    TArray<TSharedPtr<FJsonValue>> CreatedNodesArray;
    int32 NodeCount = 0;
    int32 ConnectionCount = 0;

    auto AddExpressionToOwner = [&](UMaterialExpression* Expression)
    {
        if (Material)
        {
            Material->GetExpressionCollection().AddExpression(Expression);
        }
        else if (MaterialFunction)
        {
            MaterialFunction->GetExpressionCollection().AddExpression(Expression);
        }
    };

    // Process nodes array
    const TArray<TSharedPtr<FJsonValue>>* NodesArray = nullptr;
    if (Params->TryGetArrayField(TEXT("nodes"), NodesArray) && NodesArray)
    {
        for (const TSharedPtr<FJsonValue>& NodeValue : *NodesArray)
        {
            if (!NodeValue.IsValid()) continue;
            
            TSharedPtr<FJsonObject> NodeObj = NodeValue->AsObject();
            if (!NodeObj.IsValid()) continue;

            // Get node ID
            FString NodeId;
            if (!NodeObj->TryGetStringField(TEXT("id"), NodeId))
            {
                continue;
            }

            // Get expression type
            FString ExpressionType;
            if (!NodeObj->TryGetStringField(TEXT("type"), ExpressionType))
            {
                continue;
            }

            // Get position
            int32 PosX = 0, PosY = 0;
            NodeObj->TryGetNumberField(TEXT("pos_x"), PosX);
            NodeObj->TryGetNumberField(TEXT("pos_y"), PosY);

            // Create expression based on type
            UMaterialExpression* NewExpression = nullptr;

            if (ExpressionType == TEXT("Constant"))
            {
                UMaterialExpressionConstant* Const = NewObject<UMaterialExpressionConstant>(GraphOwner);
                float Value = 0.0f;
                NodeObj->TryGetNumberField(TEXT("value"), Value);
                Const->R = Value;
                NewExpression = Const;
            }
            else if (ExpressionType == TEXT("Constant2Vector"))
            {
                UMaterialExpressionConstant2Vector* Const2 = NewObject<UMaterialExpressionConstant2Vector>(GraphOwner);
                const TArray<TSharedPtr<FJsonValue>>* ValueArray = nullptr;
                if (NodeObj->TryGetArrayField(TEXT("value"), ValueArray) && ValueArray && ValueArray->Num() >= 2)
                {
                    Const2->R = (*ValueArray)[0]->AsNumber();
                    Const2->G = (*ValueArray)[1]->AsNumber();
                }
                NewExpression = Const2;
            }
            else if (ExpressionType == TEXT("Constant3Vector"))
            {
                UMaterialExpressionConstant3Vector* Const3 = NewObject<UMaterialExpressionConstant3Vector>(GraphOwner);
                const TArray<TSharedPtr<FJsonValue>>* ValueArray = nullptr;
                if (NodeObj->TryGetArrayField(TEXT("value"), ValueArray) && ValueArray && ValueArray->Num() >= 3)
                {
                    Const3->Constant.R = (*ValueArray)[0]->AsNumber();
                    Const3->Constant.G = (*ValueArray)[1]->AsNumber();
                    Const3->Constant.B = (*ValueArray)[2]->AsNumber();
                }
                NewExpression = Const3;
            }
            else if (ExpressionType == TEXT("Constant4Vector"))
            {
                UMaterialExpressionConstant4Vector* Const4 = NewObject<UMaterialExpressionConstant4Vector>(GraphOwner);
                const TArray<TSharedPtr<FJsonValue>>* ValueArray = nullptr;
                if (NodeObj->TryGetArrayField(TEXT("value"), ValueArray) && ValueArray && ValueArray->Num() >= 4)
                {
                    Const4->Constant.R = (*ValueArray)[0]->AsNumber();
                    Const4->Constant.G = (*ValueArray)[1]->AsNumber();
                    Const4->Constant.B = (*ValueArray)[2]->AsNumber();
                    Const4->Constant.A = (*ValueArray)[3]->AsNumber();
                }
                NewExpression = Const4;
            }
            else if (ExpressionType == TEXT("Multiply"))
            {
                NewExpression = NewObject<UMaterialExpressionMultiply>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Add"))
            {
                NewExpression = NewObject<UMaterialExpressionAdd>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Subtract"))
            {
                NewExpression = NewObject<UMaterialExpressionSubtract>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Divide"))
            {
                NewExpression = NewObject<UMaterialExpressionDivide>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Lerp"))
            {
                NewExpression = NewObject<UMaterialExpressionLinearInterpolate>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Clamp"))
            {
                NewExpression = NewObject<UMaterialExpressionClamp>(GraphOwner);
            }
            else if (ExpressionType == TEXT("TextureSample"))
            {
                UMaterialExpressionTextureSample* TexExpr = NewObject<UMaterialExpressionTextureSample>(GraphOwner);
                FString TexturePath;
                UTexture* Texture = nullptr;
                if (NodeObj->TryGetStringField(TEXT("texture"), TexturePath))
                {
                    Texture = Cast<UTexture>(UEditorAssetLibrary::LoadAsset(TexturePath));
                    if (Texture)
                    {
                        TexExpr->Texture = Texture;
                    }
                }
                FString SamplerTypeName;
                if (NodeObj->TryGetStringField(TEXT("sampler_type"), SamplerTypeName))
                {
                    TexExpr->SamplerType = ResolveTextureSamplerType(SamplerTypeName, Texture);
                }
                else
                {
                    TexExpr->SamplerType = ResolveTextureSamplerType(TEXT(""), Texture);
                }
                NewExpression = TexExpr;
            }
            else if (ExpressionType == TEXT("TextureSampleParameter2D") || ExpressionType == TEXT("TextureParameter"))
            {
                UMaterialExpressionTextureSampleParameter2D* TexParam = NewObject<UMaterialExpressionTextureSampleParameter2D>(GraphOwner);
                FString TexturePath;
                UTexture* Texture = nullptr;
                if (NodeObj->TryGetStringField(TEXT("texture"), TexturePath))
                {
                    Texture = Cast<UTexture>(UEditorAssetLibrary::LoadAsset(TexturePath));
                    if (Texture)
                    {
                        TexParam->Texture = Texture;
                    }
                }

                FString ParamName;
                if (NodeObj->TryGetStringField(TEXT("parameter_name"), ParamName))
                {
                    TexParam->ParameterName = FName(*ParamName);
                }

                FString Group;
                if (NodeObj->TryGetStringField(TEXT("group"), Group))
                {
                    TexParam->Group = FName(*Group);
                }

                FString SamplerTypeName;
                if (NodeObj->TryGetStringField(TEXT("sampler_type"), SamplerTypeName))
                {
                    TexParam->SamplerType = ResolveTextureSamplerType(SamplerTypeName, Texture);
                }
                else
                {
                    TexParam->SamplerType = ResolveTextureSamplerType(TEXT(""), Texture);
                }

                NewExpression = TexParam;
            }
            else if (ExpressionType == TEXT("ScalarParameter"))
            {
                UMaterialExpressionScalarParameter* ScalarParam = NewObject<UMaterialExpressionScalarParameter>(GraphOwner);
                FString ParamName;
                if (NodeObj->TryGetStringField(TEXT("parameter_name"), ParamName))
                {
                    ScalarParam->ParameterName = FName(*ParamName);
                }
                float DefaultValue = 0.0f;
                if (NodeObj->TryGetNumberField(TEXT("value"), DefaultValue))
                {
                    ScalarParam->DefaultValue = DefaultValue;
                }
                FString Group;
                if (NodeObj->TryGetStringField(TEXT("group"), Group))
                {
                    ScalarParam->Group = FName(*Group);
                }
                NewExpression = ScalarParam;
            }
            else if (ExpressionType == TEXT("VectorParameter"))
            {
                UMaterialExpressionVectorParameter* VectorParam = NewObject<UMaterialExpressionVectorParameter>(GraphOwner);
                FString ParamName;
                if (NodeObj->TryGetStringField(TEXT("parameter_name"), ParamName))
                {
                    VectorParam->ParameterName = FName(*ParamName);
                }
                const TArray<TSharedPtr<FJsonValue>>* ValueArray = nullptr;
                if (NodeObj->TryGetArrayField(TEXT("value"), ValueArray) && ValueArray && ValueArray->Num() >= 4)
                {
                    VectorParam->DefaultValue.R = (*ValueArray)[0]->AsNumber();
                    VectorParam->DefaultValue.G = (*ValueArray)[1]->AsNumber();
                    VectorParam->DefaultValue.B = (*ValueArray)[2]->AsNumber();
                    VectorParam->DefaultValue.A = (*ValueArray)[3]->AsNumber();
                }
                FString Group;
                if (NodeObj->TryGetStringField(TEXT("group"), Group))
                {
                    VectorParam->Group = FName(*Group);
                }
                NewExpression = VectorParam;
            }
            else if (ExpressionType == TEXT("TextureCoordinate"))
            {
                NewExpression = NewObject<UMaterialExpressionTextureCoordinate>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Time"))
            {
                NewExpression = NewObject<UMaterialExpressionTime>(GraphOwner);
            }
            else if (ExpressionType == TEXT("VertexNormal"))
            {
                NewExpression = NewObject<UMaterialExpressionVertexNormalWS>(GraphOwner);
            }
            else if (ExpressionType == TEXT("WorldPosition"))
            {
                NewExpression = NewObject<UMaterialExpressionWorldPosition>(GraphOwner);
            }
            else if (ExpressionType == TEXT("OneMinus"))
            {
                NewExpression = NewObject<UMaterialExpressionOneMinus>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Saturate"))
            {
                NewExpression = NewObject<UMaterialExpressionSaturate>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Normalize"))
            {
                NewExpression = NewObject<UMaterialExpressionNormalize>(GraphOwner);
            }
            else if (ExpressionType == TEXT("DotProduct"))
            {
                NewExpression = NewObject<UMaterialExpressionDotProduct>(GraphOwner);
            }
            else if (ExpressionType == TEXT("CrossProduct"))
            {
                NewExpression = NewObject<UMaterialExpressionCrossProduct>(GraphOwner);
            }
            else if (ExpressionType == TEXT("ComponentMask"))
            {
                UMaterialExpressionComponentMask* Mask = NewObject<UMaterialExpressionComponentMask>(GraphOwner);
                bool bR = false, bG = false, bB = false, bA = false;
                NodeObj->TryGetBoolField(TEXT("mask_r"), bR);
                NodeObj->TryGetBoolField(TEXT("mask_g"), bG);
                NodeObj->TryGetBoolField(TEXT("mask_b"), bB);
                NodeObj->TryGetBoolField(TEXT("mask_a"), bA);
                Mask->R = bR;
                Mask->G = bG;
                Mask->B = bB;
                Mask->A = bA;
                NewExpression = Mask;
            }
            else if (ExpressionType == TEXT("AppendVector"))
            {
                NewExpression = NewObject<UMaterialExpressionAppendVector>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Fresnel"))
            {
                NewExpression = NewObject<UMaterialExpressionFresnel>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Power"))
            {
                NewExpression = NewObject<UMaterialExpressionPower>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Panner"))
            {
                NewExpression = NewObject<UMaterialExpressionPanner>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Rotator"))
            {
                NewExpression = NewObject<UMaterialExpressionRotator>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Sine"))
            {
                NewExpression = NewObject<UMaterialExpressionSine>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Cosine"))
            {
                NewExpression = NewObject<UMaterialExpressionCosine>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Abs"))
            {
                NewExpression = NewObject<UMaterialExpressionAbs>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Floor"))
            {
                NewExpression = NewObject<UMaterialExpressionFloor>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Ceil"))
            {
                NewExpression = NewObject<UMaterialExpressionCeil>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Frac"))
            {
                NewExpression = NewObject<UMaterialExpressionFrac>(GraphOwner);
            }
            else if (ExpressionType == TEXT("SquareRoot"))
            {
                NewExpression = NewObject<UMaterialExpressionSquareRoot>(GraphOwner);
            }
            else if (ExpressionType == TEXT("Desaturation"))
            {
                NewExpression = NewObject<UMaterialExpressionDesaturation>(GraphOwner);
            }
            else if (ExpressionType == TEXT("ReflectionVector"))
            {
                NewExpression = NewObject<UMaterialExpressionReflectionVectorWS>(GraphOwner);
            }
            else if (ExpressionType == TEXT("CameraPosition"))
            {
                NewExpression = NewObject<UMaterialExpressionCameraPositionWS>(GraphOwner);
            }
            else if (ExpressionType == TEXT("CameraVector"))
            {
                NewExpression = NewObject<UMaterialExpressionCameraVectorWS>(GraphOwner);
            }
            else if (ExpressionType == TEXT("FunctionInput"))
            {
                UMaterialExpressionFunctionInput* FunctionInput = NewObject<UMaterialExpressionFunctionInput>(GraphOwner);
                FString InputName;
                if (NodeObj->TryGetStringField(TEXT("input_name"), InputName) || NodeObj->TryGetStringField(TEXT("name"), InputName))
                {
                    FunctionInput->InputName = FName(*InputName);
                }

                FString Description;
                if (NodeObj->TryGetStringField(TEXT("description"), Description))
                {
                    FunctionInput->Description = Description;
                }

                FString InputTypeName;
                if (NodeObj->TryGetStringField(TEXT("input_type"), InputTypeName) || NodeObj->TryGetStringField(TEXT("type_name"), InputTypeName))
                {
                    FunctionInput->InputType = ResolveFunctionInputType(InputTypeName);
                }

                int32 SortPriority = 0;
                if (NodeObj->TryGetNumberField(TEXT("sort_priority"), SortPriority))
                {
                    FunctionInput->SortPriority = SortPriority;
                }

                const TArray<TSharedPtr<FJsonValue>>* PreviewValueArray = nullptr;
                if (NodeObj->TryGetArrayField(TEXT("preview_value"), PreviewValueArray) && PreviewValueArray && PreviewValueArray->Num() >= 4)
                {
                    FunctionInput->PreviewValue.X = (*PreviewValueArray)[0]->AsNumber();
                    FunctionInput->PreviewValue.Y = (*PreviewValueArray)[1]->AsNumber();
                    FunctionInput->PreviewValue.Z = (*PreviewValueArray)[2]->AsNumber();
                    FunctionInput->PreviewValue.W = (*PreviewValueArray)[3]->AsNumber();
                }

                bool bUsePreviewValueAsDefault = false;
                if (NodeObj->TryGetBoolField(TEXT("use_preview_value_as_default"), bUsePreviewValueAsDefault))
                {
                    FunctionInput->bUsePreviewValueAsDefault = bUsePreviewValueAsDefault ? 1 : 0;
                }

                FunctionInput->ConditionallyGenerateId(true);
                NewExpression = FunctionInput;
            }
            else if (ExpressionType == TEXT("FunctionOutput"))
            {
                UMaterialExpressionFunctionOutput* FunctionOutput = NewObject<UMaterialExpressionFunctionOutput>(GraphOwner);
                FString OutputName;
                if (NodeObj->TryGetStringField(TEXT("output_name"), OutputName) || NodeObj->TryGetStringField(TEXT("name"), OutputName))
                {
                    FunctionOutput->OutputName = FName(*OutputName);
                }

                FString Description;
                if (NodeObj->TryGetStringField(TEXT("description"), Description))
                {
                    FunctionOutput->Description = Description;
                }

                int32 SortPriority = 0;
                if (NodeObj->TryGetNumberField(TEXT("sort_priority"), SortPriority))
                {
                    FunctionOutput->SortPriority = SortPriority;
                }

                FunctionOutput->ConditionallyGenerateId(true);
                NewExpression = FunctionOutput;
            }
            else if (ExpressionType == TEXT("Custom"))
            {
                UMaterialExpressionCustom* CustomExpression = NewObject<UMaterialExpressionCustom>(GraphOwner);
                FString Code;
                if (NodeObj->TryGetStringField(TEXT("code"), Code))
                {
                    CustomExpression->Code = Code;
                }

                FString Description;
                if (NodeObj->TryGetStringField(TEXT("description"), Description))
                {
                    CustomExpression->Description = Description;
                }

                FString OutputTypeName;
                if (NodeObj->TryGetStringField(TEXT("output_type"), OutputTypeName))
                {
                    CustomExpression->OutputType = ResolveCustomOutputType(OutputTypeName);
                }

                const TArray<TSharedPtr<FJsonValue>>* IncludeFilePaths = nullptr;
                if (NodeObj->TryGetArrayField(TEXT("include_file_paths"), IncludeFilePaths) && IncludeFilePaths && IncludeFilePaths->Num() > 0)
                {
                    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Custom node include_file_paths are not supported; use inline code only"));
                }

                const TArray<TSharedPtr<FJsonValue>>* CustomInputs = nullptr;
                if (NodeObj->TryGetArrayField(TEXT("inputs"), CustomInputs) && CustomInputs)
                {
                    for (const TSharedPtr<FJsonValue>& InputValue : *CustomInputs)
                    {
                        if (!InputValue.IsValid())
                        {
                            continue;
                        }

                        TSharedPtr<FJsonObject> InputObj = InputValue->AsObject();
                        if (!InputObj.IsValid())
                        {
                            continue;
                        }

                        FString InputName;
                        if (!InputObj->TryGetStringField(TEXT("input_name"), InputName) && !InputObj->TryGetStringField(TEXT("name"), InputName))
                        {
                            continue;
                        }

                        FCustomInput& NewInput = CustomExpression->Inputs.AddDefaulted_GetRef();
                        NewInput.InputName = FName(*InputName);
                    }
                }

#if WITH_EDITOR
                CustomExpression->RebuildOutputs();
#endif
                NewExpression = CustomExpression;
            }
            else if (ExpressionType == TEXT("MaterialFunctionCall"))
            {
                UMaterialExpressionMaterialFunctionCall* FunctionCall = NewObject<UMaterialExpressionMaterialFunctionCall>(GraphOwner);
                FString FunctionPath;
                if (!NodeObj->TryGetStringField(TEXT("material_function"), FunctionPath) &&
                    !NodeObj->TryGetStringField(TEXT("function_path"), FunctionPath) &&
                    !NodeObj->TryGetStringField(TEXT("material_function_path"), FunctionPath))
                {
                    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("MaterialFunctionCall node is missing 'material_function' or 'function_path'"));
                }

                UMaterialFunction* FunctionAsset = Cast<UMaterialFunction>(UEditorAssetLibrary::LoadAsset(FunctionPath));
                if (!FunctionAsset)
                {
                    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Failed to load material function: %s"), *FunctionPath));
                }

                if (!FunctionCall->SetMaterialFunction(FunctionAsset))
                {
                    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Failed to assign material function: %s"), *FunctionPath));
                }

                FunctionCall->UpdateFromFunctionResource();
                NewExpression = FunctionCall;
            }
            else
            {
                return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unsupported expression type: %s"), *ExpressionType));
            }

            if (NewExpression)
            {
                // Set position
                NewExpression->MaterialExpressionEditorX = PosX;
                NewExpression->MaterialExpressionEditorY = PosY;

                // Add to graph owner
                AddExpressionToOwner(NewExpression);

                // Store in map
                NodeIdToExpression.Add(NodeId, NewExpression);

                // Track created node
                TSharedPtr<FJsonObject> CreatedNodeObj = MakeShared<FJsonObject>();
                CreatedNodeObj->SetStringField(TEXT("id"), NodeId);
                CreatedNodeObj->SetStringField(TEXT("type"), ExpressionType);
                FString ActualNodeId = FString::Printf(TEXT("Expr_%s_%d"), *ExpressionType, NewExpression->GetUniqueID());
                CreatedNodeObj->SetStringField(TEXT("node_id"), ActualNodeId);
                CreatedNodesArray.Add(MakeShared<FJsonValueObject>(CreatedNodeObj));

                NodeCount++;
            }
        }
    }

    // Process connections array
    const TArray<TSharedPtr<FJsonValue>>* ConnectionsArray = nullptr;
    if (Params->TryGetArrayField(TEXT("connections"), ConnectionsArray) && ConnectionsArray)
    {
        for (const TSharedPtr<FJsonValue>& ConnValue : *ConnectionsArray)
        {
            if (!ConnValue.IsValid()) continue;
            
            TSharedPtr<FJsonObject> ConnObj = ConnValue->AsObject();
            if (!ConnObj.IsValid()) continue;

            FString SourceId, TargetId;
            if (!ConnObj->TryGetStringField(TEXT("source"), SourceId) || 
                !ConnObj->TryGetStringField(TEXT("target"), TargetId))
            {
                continue;
            }

            FString SourceOutput = TEXT("Output");
            ConnObj->TryGetStringField(TEXT("source_output"), SourceOutput);

            FString TargetInput;
            ConnObj->TryGetStringField(TEXT("target_input"), TargetInput);

            // Handle connection to material property
            if (TargetId == TEXT("Material"))
            {
                if (!Material)
                {
                    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Material property connections are only valid for UMaterial targets"));
                }

                UMaterialExpression** SourceExpr = NodeIdToExpression.Find(SourceId);
                if (SourceExpr && *SourceExpr)
                {
                    FExpressionInput* PropertyInput = GetMaterialPropertyInput(Material, TargetInput);
                    if (!PropertyInput)
                    {
                        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown material property input: %s"), *TargetInput));
                    }

                    PropertyInput->Expression = *SourceExpr;
                    PropertyInput->OutputIndex = GetExpressionOutputIndexByName(*SourceExpr, SourceOutput);
                    ConnectionCount++;
                }
            }
            else
            {
                // Handle node-to-node connection
                UMaterialExpression** SourceExpr = NodeIdToExpression.Find(SourceId);
                UMaterialExpression** TargetExpr = NodeIdToExpression.Find(TargetId);

                if (SourceExpr && TargetExpr && *SourceExpr && *TargetExpr)
                {
                    FExpressionInput* InputPtr = GetExpressionInputByName(*TargetExpr, TargetInput);
                    if (!InputPtr)
                    {
                        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown target input '%s' on node '%s'"), *TargetInput, *TargetId));
                    }

                    InputPtr->Expression = *SourceExpr;
                    InputPtr->OutputIndex = GetExpressionOutputIndexByName(*SourceExpr, SourceOutput);
                    ConnectionCount++;
                }
            }
        }
    }

    // Process material properties if provided
    const TSharedPtr<FJsonObject>* PropertiesObj = nullptr;
    if (Params->TryGetObjectField(TEXT("properties"), PropertiesObj))
    {
        if (!Material)
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Material properties can only be applied to UMaterial targets"));
        }

        // Shading Model
        FString ShadingModel;
        if ((*PropertiesObj)->TryGetStringField(TEXT("shading_model"), ShadingModel))
        {
            if (ShadingModel == TEXT("Unlit"))
                Material->SetShadingModel(EMaterialShadingModel::MSM_Unlit);
            else if (ShadingModel == TEXT("DefaultLit"))
                Material->SetShadingModel(EMaterialShadingModel::MSM_DefaultLit);
            else if (ShadingModel == TEXT("Subsurface"))
                Material->SetShadingModel(EMaterialShadingModel::MSM_Subsurface);
            else if (ShadingModel == TEXT("TwoSidedFoliage"))
                Material->SetShadingModel(EMaterialShadingModel::MSM_TwoSidedFoliage);
        }

        // Blend Mode
        FString BlendMode;
        if ((*PropertiesObj)->TryGetStringField(TEXT("blend_mode"), BlendMode))
        {
            if (BlendMode == TEXT("Opaque"))
                Material->BlendMode = EBlendMode::BLEND_Opaque;
            else if (BlendMode == TEXT("Masked"))
                Material->BlendMode = EBlendMode::BLEND_Masked;
            else if (BlendMode == TEXT("Translucent"))
                Material->BlendMode = EBlendMode::BLEND_Translucent;
            else if (BlendMode == TEXT("Additive"))
                Material->BlendMode = EBlendMode::BLEND_Additive;
        }

        // Two Sided
        bool bTwoSided;
        if ((*PropertiesObj)->TryGetBoolField(TEXT("two_sided"), bTwoSided))
        {
            Material->TwoSided = bTwoSided ? 1 : 0;
        }

        // Material Domain
        FString MaterialDomain;
        if ((*PropertiesObj)->TryGetStringField(TEXT("material_domain"), MaterialDomain))
        {
            if (MaterialDomain == TEXT("Surface"))
                Material->MaterialDomain = (EMaterialDomain)0;
            else if (MaterialDomain == TEXT("DeferredDecal"))
                Material->MaterialDomain = (EMaterialDomain)1;
            else if (MaterialDomain == TEXT("LightFunction"))
                Material->MaterialDomain = (EMaterialDomain)2;
            else if (MaterialDomain == TEXT("PostProcess"))
                Material->MaterialDomain = (EMaterialDomain)4;
        }
    }

    if (Material)
    {
        Material->MarkPackageDirty();
        UEditorAssetLibrary::SaveAsset(MaterialPath, false);
    }
    else if (MaterialFunction)
    {
        MaterialFunction->MarkPackageDirty();
        MaterialFunction->UpdateFromFunctionResource();
        UEditorAssetLibrary::SaveAsset(MaterialPath, false);
    }

    // Compile if requested
    bool bShouldCompile = true;
    Params->TryGetBoolField(TEXT("compile"), bShouldCompile);
    if (bShouldCompile && Material)
    {
        Material->ForceRecompileForRendering();
    }

    // Build result
    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("material_name"), MaterialName);
    ResultObj->SetStringField(TEXT("asset_type"), Material ? TEXT("Material") : TEXT("MaterialFunction"));
    ResultObj->SetNumberField(TEXT("node_count"), NodeCount);
    ResultObj->SetNumberField(TEXT("connection_count"), ConnectionCount);
    ResultObj->SetArrayField(TEXT("nodes"), CreatedNodesArray);
    ResultObj->SetBoolField(TEXT("compiled"), bShouldCompile && Material);
    ResultObj->SetBoolField(TEXT("success"), true);

    return ResultObj;
}
