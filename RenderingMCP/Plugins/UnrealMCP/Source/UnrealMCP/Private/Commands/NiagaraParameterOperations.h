#pragma once

#include "NiagaraNodeAssignment.h"
#include "NiagaraNodeFunctionCall.h"
#include "NiagaraGraph.h"
#include "NiagaraScriptSource.h"
#include "NiagaraParameterStore.h"
#include "ViewModels/Stack/NiagaraStackGraphUtilities.h"
#include "../Private/NiagaraNodeParameterMapGet.h"

namespace MCPNiagaraParameters
{
inline TSharedPtr<FJsonObject> Failure(const FString& Message)
{
    auto Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), false);
    Result->SetStringField(TEXT("error"), Message);
    return Result;
}

inline TArray<UEdGraphPin*> FindPins(UNiagaraGraph& Graph, FName Name)
{
    TArray<UEdGraphPin*> Result;
    for (UEdGraphNode* Node : Graph.Nodes)
        for (UEdGraphPin* Pin : Node->Pins)
            if (Pin->PinName == Name) Result.Add(Pin);
    return Result;
}

inline TSharedPtr<FJsonObject> Snapshot(UNiagaraGraph& Graph)
{
    auto Result = MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> Assignments;
    for (UEdGraphNode* Node : Graph.Nodes)
    {
        if (auto* Assignment = Cast<UNiagaraNodeAssignment>(Node))
        {
            for (int32 Index = 0; Index < Assignment->NumTargets(); ++Index)
            {
                const FNiagaraVariable& Var = Assignment->GetAssignmentTarget(Index);
                auto Item = MakeShared<FJsonObject>();
                Item->SetStringField(TEXT("node"), Assignment->GetName());
                Item->SetStringField(TEXT("name"), Var.GetName().ToString());
                Item->SetStringField(TEXT("type"), Var.GetType().GetName());
                Item->SetStringField(TEXT("default"), Assignment->GetAssignmentDefaults()[Index]);
                const FString Alias = Assignment->GetFunctionName() + TEXT(".") + Var.GetName().ToString();
                TArray<TSharedPtr<FJsonValue>> Links;
                for (UEdGraphPin* Pin : FindPins(Graph, FName(*Alias)))
                    for (UEdGraphPin* Link : Pin->LinkedTo)
                    {
                        Links.Add(MakeShared<FJsonValueString>(Link->GetOwningNode()->GetName() + TEXT(".") + Link->PinName.ToString()));
                        if (auto* Dynamic = Cast<UNiagaraNodeFunctionCall>(Link->GetOwningNode()))
                        {
                            if (Dynamic->FunctionScript && Dynamic->FunctionScript->GetPathName() == TEXT("/Niagara/DynamicInputs/Transforms/TransformPosition.TransformPosition"))
                            {
                                auto Inputs = MakeShared<FJsonObject>();
                                for (const FString& Name : {FString(TEXT("Position")), FString(TEXT("Source Space")), FString(TEXT("Destination Space")), FString(TEXT("Apply Scale"))})
                                {
                                    for (UEdGraphPin* Input : FindPins(Graph, FName(*(Dynamic->GetFunctionName() + TEXT(".") + Name))))
                                    {
                                        FString Value = Input->DefaultValue;
                                        if (!Input->LinkedTo.IsEmpty()) Value = Input->LinkedTo[0]->PinName.ToString();
                                        else if (const UEnum* Enum = Cast<UEnum>(Input->PinType.PinSubCategoryObject.Get()))
                                        {
                                            const int64 EnumValue = Enum->GetValueByNameString(Value);
                                            Value = EnumValue == INDEX_NONE ? TEXT("<invalid enum>") : Enum->GetDisplayNameTextByValue(EnumValue).ToString();
                                        }
                                        Inputs->SetStringField(Name, Value);
                                    }
                                }
                                Item->SetObjectField(TEXT("transform_inputs"), Inputs);
                            }
                        }
                    }
                Item->SetArrayField(TEXT("input_links"), Links);
                Assignments.Add(MakeShared<FJsonValueObject>(Item));
            }
        }
    }
    Result->SetArrayField(TEXT("assignments"), Assignments);
    return Result;
}

inline TSharedPtr<FJsonObject> Rename(UNiagaraSystem& System, FNiagaraEmitterHandle& Handle, UNiagaraGraph& Graph, const FJsonObject& Op)
{
    FString OldName, NewName;
    bool Replace = false, DryRun = true;
    Op.TryGetBoolField(TEXT("replace_existing"), Replace);
    Op.TryGetBoolField(TEXT("dry_run"), DryRun);
    if (!Op.TryGetStringField(TEXT("old_name"), OldName) || !Op.TryGetStringField(TEXT("new_name"), NewName) ||
        !OldName.StartsWith(TEXT("Particles.")) || !NewName.StartsWith(TEXT("Particles.")) || OldName.Len() <= 10 || NewName.Len() <= 10 || FName(*OldName) == FName(*NewName))
        return Failure(TEXT("Distinct Particles.* old_name and new_name are required"));
    TArray<UNiagaraNodeAssignment*> Targets;
    FNiagaraVariable OldVariable;
    int32 Conflicts = 0;
    for (UEdGraphNode* Node : Graph.Nodes)
    {
        auto* Assignment = Cast<UNiagaraNodeAssignment>(Node);
        if (!Assignment) continue;
        const int32 OldIndex = Assignment->FindAssignmentTarget(FName(*OldName));
        const int32 NewIndex = Assignment->FindAssignmentTarget(FName(*NewName));
        if (NewIndex != INDEX_NONE)
        {
            if (!Replace || OldIndex == INDEX_NONE)
                return Failure(TEXT("Destination already has a writer; replacement is allowed only within the same assignment node"));
            if (Assignment->GetAssignmentTarget(NewIndex).GetType() != Assignment->GetAssignmentTarget(OldIndex).GetType())
                return Failure(TEXT("Destination has an incompatible type"));
            const FString Alias = Assignment->GetFunctionName() + TEXT(".") + NewName;
            for (UEdGraphPin* Pin : FindPins(Graph, FName(*Alias)))
                if (Pin->LinkedTo.Num() != 0)
                    return Failure(TEXT("Destination has a connected input; refusing to discard its graph"));
            ++Conflicts;
        }
        if (OldIndex != INDEX_NONE)
        {
            const FNiagaraVariable& Var = Assignment->GetAssignmentTarget(OldIndex);
            if (OldVariable.IsValid() && OldVariable.GetType() != Var.GetType()) return Failure(TEXT("Source has conflicting types"));
            OldVariable = Var;
            Targets.Add(Assignment);
        }
    }
    if (Targets.IsEmpty()) return Failure(TEXT("Source assignment not found"));
    auto Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetBoolField(TEXT("dry_run"), DryRun);
    Result->SetNumberField(TEXT("renamed_assignments"), Targets.Num());
    Result->SetNumberField(TEXT("replaced_assignments"), Conflicts);
    Result->SetObjectField(TEXT("before"), Snapshot(Graph));
    if (DryRun) return Result;

    if (GEditor) GEditor->GetEditorSubsystem<UAssetEditorSubsystem>()->CloseAllEditorsForAsset(&System);
    FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "RenameParticleParameter", "Rename Niagara particle parameter"));
    System.Modify(); Graph.Modify();
    TArray<UNiagaraScript*> Scripts;
    Handle.GetEmitterData()->GetScripts(Scripts, false);
    for (UNiagaraNodeAssignment* Assignment : Targets)
    {
        Assignment->Modify();
        const FString OldAlias = Assignment->GetFunctionName() + TEXT(".") + OldName;
        const FString NewAlias = Assignment->GetFunctionName() + TEXT(".") + NewName;
        const int32 NewIndex = Assignment->FindAssignmentTarget(FName(*NewName));
        if (NewIndex != INDEX_NONE)
        {
            const FNiagaraVariable Existing = Assignment->GetAssignmentTarget(NewIndex);
            for (UEdGraphPin* Pin : FindPins(Graph, FName(*NewAlias)))
            {
                Pin->Modify(); Pin->GetOwningNode()->Modify();
                Pin->GetOwningNode()->RemovePin(Pin);
            }
            Assignment->RemoveParameter(Existing);
        }
        // Preserve linked dynamic inputs by renaming their override pin, not recreating them.
        for (UEdGraphPin* Pin : FindPins(Graph, FName(*OldAlias)))
        {
            Pin->Modify(); Pin->PinName = FName(*NewAlias);
        }
        for (UNiagaraScript* Script : Scripts)
        {
            Script->Modify();
            TArray<FNiagaraVariable> Remove, Rename;
            for (const FNiagaraVariableWithOffset& Var : Script->RapidIterationParameters.ReadParameterVariables())
            {
                if (Var.GetName().ToString().EndsWith(TEXT(".") + NewAlias)) Remove.Add(Var);
                if (Var.GetName().ToString().EndsWith(TEXT(".") + OldAlias)) Rename.Add(Var);
            }
            for (const FNiagaraVariable& Var : Remove) Script->RapidIterationParameters.RemoveParameter(Var);
            for (const FNiagaraVariable& Var : Rename)
            {
                FString Name = Var.GetName().ToString();
                Name.LeftChopInline(OldAlias.Len()); Name += NewAlias;
                Script->RapidIterationParameters.RenameParameter(Var, FName(*Name));
            }
        }
        Assignment->RenameAssignmentTarget(FName(*OldName), FName(*NewName));
        Assignment->RefreshFromExternalChanges();
    }
    Graph.RenameParameter(OldVariable, FName(*NewName));
    System.RequestCompile(true);
    System.WaitForCompilationComplete(false, false);
    Result->SetBoolField(TEXT("compiled"), System.IsReadyToRun());
    Result->SetBoolField(TEXT("success"), System.IsReadyToRun());
    Result->SetObjectField(TEXT("post_state"), Snapshot(Graph));
    return Result;
}

inline FNiagaraTypeDefinition InputType(UNiagaraScript& Script, const FString& Name)
{
    auto* Source = Cast<UNiagaraScriptSource>(Script.GetLatestSource());
    if (Source && Source->NodeGraph)
        for (const auto& Entry : Source->NodeGraph->GetAllMetaData())
            if (Entry.Key.GetName() == FName(*(TEXT("Module.") + Name))) return Entry.Key.GetType();
    return FNiagaraTypeDefinition();
}

inline void LinkParameter(UNiagaraGraph& Graph, UEdGraphPin& Override, const FNiagaraVariable& Source)
{
    FGraphNodeCreator<UNiagaraNodeParameterMapGet> Creator(Graph);
    auto* Get = Creator.CreateNode(); Creator.Finalize();
    UEdGraphPin* Output = Get->GetOutputPin(0); // The node's native Add pin.
    UEdGraphPin* MapInput = Get->GetInputPin(0);
    UEdGraphNode* Owner = Override.GetOwningNode();
    for (UEdGraphPin* Pin : Owner->Pins)
    {
        if (Pin->Direction == EGPD_Input && Pin != &Override && Pin->PinType == MapInput->PinType && !Pin->LinkedTo.IsEmpty())
        {
            Pin->LinkedTo[0]->MakeLinkTo(MapInput);
            break;
        }
    }
    Output->MakeLinkTo(&Override);
    // Use the native connection-change path to create the typed pin and its
    // paired default pin; RequestNewTypedPin itself is not exported by UE.
    static_cast<UEdGraphNode*>(Get)->PinConnectionListChanged(Output);
    for (UEdGraphPin* Link : Override.LinkedTo)
    {
        if (Link->GetOwningNode() == Get)
        {
            // This is a newly created read pin, not a user parameter rename.
            // CommitEditablePinName invokes parameter-definition subscriptions
            // and requires an editor view model, which headless MCP does not own.
            Link->Modify();
            Link->PinName = Source.GetName();
            Link->PinFriendlyName = FText::FromName(Source.GetName());
            break;
        }
    }
}

inline TSharedPtr<FJsonObject> BindPosition(UNiagaraSystem& System, UNiagaraGraph& Graph, const FJsonObject& Op)
{
    FString NodeName, TargetName, SourceName;
    bool WorldSpace = false, DryRun = true;
    Op.TryGetBoolField(TEXT("world_space"), WorldSpace); Op.TryGetBoolField(TEXT("dry_run"), DryRun);
    if (!Op.TryGetStringField(TEXT("module_name"), NodeName) || !Op.TryGetStringField(TEXT("target"), TargetName) || !Op.TryGetStringField(TEXT("source"), SourceName) || SourceName != TEXT("Particles.Position"))
        return Failure(TEXT("module_name, target and source=Particles.Position are required"));
    UNiagaraNodeAssignment* Assignment = nullptr;
    for (UEdGraphNode* Node : Graph.Nodes) if (Node->GetName() == NodeName) Assignment = Cast<UNiagaraNodeAssignment>(Node);
    if (!Assignment) return Failure(TEXT("Assignment module not found"));
    const int32 Index = Assignment->FindAssignmentTarget(FName(*TargetName));
    if (Index == INDEX_NONE || Assignment->GetAssignmentTarget(Index).GetType() != FNiagaraTypeDefinition::GetPositionDef())
        return Failure(TEXT("Target must be an existing position assignment"));
    const FString Alias = Assignment->GetFunctionName() + TEXT(".") + TargetName;
    UNiagaraScript* Transform = WorldSpace ? LoadObject<UNiagaraScript>(nullptr, TEXT("/Niagara/DynamicInputs/Transforms/TransformPosition.TransformPosition")) : nullptr;
    if (WorldSpace && !Transform) return Failure(TEXT("TransformPosition script missing"));
    UNiagaraNodeFunctionCall* ExistingDynamic = nullptr;
    for (UEdGraphPin* Pin : FindPins(Graph, FName(*Alias)))
    {
        if (Pin->LinkedTo.IsEmpty()) continue;
        if (Pin->LinkedTo.Num() != 1 || !Transform) return Failure(TEXT("Target already has a connected override"));
        ExistingDynamic = Cast<UNiagaraNodeFunctionCall>(Pin->LinkedTo[0]->GetOwningNode());
        if (!ExistingDynamic || ExistingDynamic->FunctionScript != Transform) return Failure(TEXT("Target is connected to a different dynamic input"));
        const FString PositionAlias = ExistingDynamic->GetFunctionName() + TEXT(".Position");
        for (UEdGraphPin* PositionPin : FindPins(Graph, FName(*PositionAlias)))
            if (!PositionPin->LinkedTo.IsEmpty() && (PositionPin->LinkedTo.Num() != 1 || PositionPin->LinkedTo[0]->PinName != FName(*SourceName)))
                return Failure(TEXT("Existing transform reads a different position source"));
    }
    FNiagaraTypeDefinition SpaceType;
    int64 SimulationValue = INDEX_NONE, WorldValue = INDEX_NONE;
    if (Transform)
    {
        SpaceType = InputType(*Transform, TEXT("Source Space"));
        const UEnum* Enum = SpaceType.GetEnum();
        if (!Enum) return Failure(TEXT("TransformPosition space input enum missing"));
        for (int32 I = 0; I < Enum->NumEnums(); ++I)
        {
            const FString Display = Enum->GetDisplayNameTextByIndex(I).ToString();
            if (Display.Equals(TEXT("Simulation"), ESearchCase::IgnoreCase)) SimulationValue = Enum->GetValueByIndex(I);
            if (Display.Equals(TEXT("World"), ESearchCase::IgnoreCase)) WorldValue = Enum->GetValueByIndex(I);
        }
        if (SimulationValue == INDEX_NONE || WorldValue == INDEX_NONE) return Failure(TEXT("Simulation/World enum values missing"));
    }
    auto Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true); Result->SetBoolField(TEXT("dry_run"), DryRun);
    Result->SetObjectField(TEXT("before"), Snapshot(Graph));
    if (DryRun) return Result;
    if (GEditor) GEditor->GetEditorSubsystem<UAssetEditorSubsystem>()->CloseAllEditorsForAsset(&System);
    FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "BindParticlePosition", "Bind Niagara particle position"));
    System.Modify(); Graph.Modify(); Assignment->Modify();
    auto& Override = FNiagaraStackGraphUtilities::GetOrCreateStackFunctionInputOverridePin(*Assignment, FNiagaraParameterHandle(*Alias), FNiagaraTypeDefinition::GetPositionDef(), FGuid(), FGuid());
    if (!Transform) LinkParameter(Graph, Override, FNiagaraVariable(FNiagaraTypeDefinition::GetPositionDef(), FName(*SourceName)));
    else
    {
        UNiagaraNodeFunctionCall* Dynamic = ExistingDynamic;
        if (!Dynamic) FNiagaraStackGraphUtilities::SetDynamicInputForFunctionInput(Override, Transform, Dynamic);
        if (!Dynamic) return Failure(TEXT("Could not create transform input"));
        auto Pin = [Dynamic](const FString& Name, FNiagaraTypeDefinition Type) -> UEdGraphPin& {
            UEdGraphPin& Input = FNiagaraStackGraphUtilities::GetOrCreateStackFunctionInputOverridePin(*Dynamic, FNiagaraParameterHandle(*(Dynamic->GetFunctionName() + TEXT(".") + Name)), Type, FGuid(), FGuid());
            Input.GetOwningNode()->Modify();
            Input.Modify();
            return Input;
        };
        UEdGraphPin& PositionPin = Pin(TEXT("Position"), FNiagaraTypeDefinition::GetPositionDef());
        if (PositionPin.LinkedTo.IsEmpty()) LinkParameter(Graph, PositionPin, FNiagaraVariable(FNiagaraTypeDefinition::GetPositionDef(), FName(*SourceName)));
        // Niagara enum pins parse enum member names, not integer strings.
        Pin(TEXT("Source Space"), SpaceType).DefaultValue = SpaceType.GetEnum()->GetNameStringByValue(SimulationValue);
        Pin(TEXT("Destination Space"), SpaceType).DefaultValue = SpaceType.GetEnum()->GetNameStringByValue(WorldValue);
        Pin(TEXT("Apply Scale"), FNiagaraTypeDefinition::GetBoolDef()).DefaultValue = TEXT("true");
    }
    Graph.NotifyGraphChanged();
    System.RequestCompile(true); System.WaitForCompilationComplete(false, false);
    Result->SetBoolField(TEXT("compiled"), System.IsReadyToRun()); Result->SetBoolField(TEXT("success"), System.IsReadyToRun());
    Result->SetObjectField(TEXT("post_state"), Snapshot(Graph));
    return Result;
}
}
