#include "Commands/BlueprintGraph/BlueprintGraphBuilderUtils.h"

#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraphSchema_K2.h"
#include "GameFramework/Actor.h"
#include "K2Node_CallFunction.h"
#include "K2Node_DynamicCast.h"
#include "K2Node_Event.h"
#include "K2Node_FunctionEntry.h"
#include "K2Node_IfThenElse.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "UObject/UnrealType.h"

namespace
{
void AddWarning(FBlueprintGraphBuildStats* Stats, const FString& Warning)
{
    if (Stats)
    {
        Stats->Warnings.Add(Warning);
    }
}

FBPVariableDescription* FindVariable(UBlueprint* Blueprint, FName VarName)
{
    if (!Blueprint)
    {
        return nullptr;
    }

    for (FBPVariableDescription& Variable : Blueprint->NewVariables)
    {
        if (Variable.VarName == VarName)
        {
            return &Variable;
        }
    }

    return nullptr;
}

template <typename TNode>
TNode* PrepareNode(UEdGraph* Graph, TNode* Node, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats, const FString& NodeComment)
{
    if (!Graph || !Node)
    {
        return nullptr;
    }

    Node->NodePosX = PosX;
    Node->NodePosY = PosY;
    Node->NodeComment = NodeComment;
    Node->CreateNewGuid();
    Graph->AddNode(Node, true, false);
    Node->PostPlacedNewNode();
    Node->AllocateDefaultPins();

    if (Stats)
    {
        Stats->NodesCreated++;
    }

    return Node;
}
}

FEdGraphPinType FBlueprintGraphBuilderUtils::MakeObjectPin(UClass* Class)
{
    FEdGraphPinType Type;
    Type.PinCategory = UEdGraphSchema_K2::PC_Object;
    Type.PinSubCategoryObject = Class;
    return Type;
}

FEdGraphPinType FBlueprintGraphBuilderUtils::MakeBoolPin()
{
    FEdGraphPinType Type;
    Type.PinCategory = UEdGraphSchema_K2::PC_Boolean;
    return Type;
}

FEdGraphPinType FBlueprintGraphBuilderUtils::MakeNamePin()
{
    FEdGraphPinType Type;
    Type.PinCategory = UEdGraphSchema_K2::PC_Name;
    return Type;
}

FEdGraphPinType FBlueprintGraphBuilderUtils::MakeFloatPin()
{
    FEdGraphPinType Type;
    Type.PinCategory = UEdGraphSchema_K2::PC_Real;
    Type.PinSubCategory = UEdGraphSchema_K2::PC_Float;
    return Type;
}

bool FBlueprintGraphBuilderUtils::SamePinType(const FEdGraphPinType& A, const FEdGraphPinType& B)
{
    return A.PinCategory == B.PinCategory &&
        A.PinSubCategory == B.PinSubCategory &&
        A.PinSubCategoryObject == B.PinSubCategoryObject &&
        A.ContainerType == B.ContainerType;
}

bool FBlueprintGraphBuilderUtils::EnsureVariable(UBlueprint* Blueprint, FName VarName, const FEdGraphPinType& VarType, const FString& Category, bool bInstanceEditable, const FString& DefaultValue, FBlueprintGraphBuildStats* Stats)
{
    if (!Blueprint)
    {
        return false;
    }

    FBPVariableDescription* Existing = FindVariable(Blueprint, VarName);
    const bool bHadExistingVariable = Existing != nullptr;
    if (!Existing)
    {
        if (!FBlueprintEditorUtils::AddMemberVariable(Blueprint, VarName, VarType, DefaultValue))
        {
            AddWarning(Stats, FString::Printf(TEXT("Failed to add variable %s"), *VarName.ToString()));
            return false;
        }

        Existing = FindVariable(Blueprint, VarName);
        if (Stats)
        {
            Stats->VariablesAdded++;
        }
    }
    else
    {
        if (!SamePinType(Existing->VarType, VarType))
        {
            Existing->VarType = VarType;
        }

        if (Stats)
        {
            Stats->VariablesUpdated++;
        }
    }

    if (!Existing)
    {
        return false;
    }

    Existing->Category = FText::FromString(Category);
    if (!bHadExistingVariable || !DefaultValue.IsEmpty())
    {
        Existing->DefaultValue = DefaultValue;
    }

    Existing->PropertyFlags |= CPF_BlueprintVisible;
    Existing->PropertyFlags &= ~CPF_BlueprintReadOnly;
    if (bInstanceEditable)
    {
        Existing->PropertyFlags |= CPF_Edit;
        Existing->PropertyFlags &= ~CPF_DisableEditOnInstance;
    }
    else
    {
        Existing->PropertyFlags &= ~CPF_Edit;
        Existing->PropertyFlags |= CPF_DisableEditOnInstance;
    }

    return true;
}

UEdGraph* FBlueprintGraphBuilderUtils::FindFunctionGraph(UBlueprint* Blueprint, FName FunctionName)
{
    if (!Blueprint)
    {
        return nullptr;
    }

    for (UEdGraph* Graph : Blueprint->FunctionGraphs)
    {
        if (Graph && Graph->GetFName() == FunctionName)
        {
            return Graph;
        }
    }

    return nullptr;
}

UEdGraph* FBlueprintGraphBuilderUtils::RecreateFunctionGraph(UBlueprint* Blueprint, FName FunctionName)
{
    if (!Blueprint)
    {
        return nullptr;
    }

    if (UEdGraph* Existing = FindFunctionGraph(Blueprint, FunctionName))
    {
        FBlueprintEditorUtils::RemoveGraph(Blueprint, Existing);
    }

    UEdGraph* NewGraph = FBlueprintEditorUtils::CreateNewGraph(
        Blueprint,
        FunctionName,
        UEdGraph::StaticClass(),
        UEdGraphSchema_K2::StaticClass());

    if (!NewGraph)
    {
        return nullptr;
    }

    FBlueprintEditorUtils::AddFunctionGraph<UClass>(Blueprint, NewGraph, true, nullptr);
    return NewGraph;
}

UK2Node_FunctionEntry* FBlueprintGraphBuilderUtils::FindFunctionEntry(UEdGraph* Graph)
{
    if (!Graph)
    {
        return nullptr;
    }

    for (UEdGraphNode* Node : Graph->Nodes)
    {
        if (UK2Node_FunctionEntry* Entry = Cast<UK2Node_FunctionEntry>(Node))
        {
            return Entry;
        }
    }

    return nullptr;
}

UEdGraphPin* FBlueprintGraphBuilderUtils::FindPin(UEdGraphNode* Node, const FString& PinName, EEdGraphPinDirection Direction)
{
    if (!Node)
    {
        return nullptr;
    }

    for (UEdGraphPin* Pin : Node->Pins)
    {
        if (Pin && Pin->PinName.ToString() == PinName && (Direction == EGPD_MAX || Pin->Direction == Direction))
        {
            return Pin;
        }
    }

    return nullptr;
}

bool FBlueprintGraphBuilderUtils::Link(UEdGraph* Graph, UEdGraphPin* Source, UEdGraphPin* Target, FBlueprintGraphBuildStats* Stats)
{
    if (!Graph || !Source || !Target)
    {
        AddWarning(Stats, TEXT("Skipped link because a pin was missing"));
        return false;
    }

    const UEdGraphSchema* Schema = Graph->GetSchema();
    if (Schema && Schema->TryCreateConnection(Source, Target))
    {
        return true;
    }

    Source->MakeLinkTo(Target);
    return true;
}

bool FBlueprintGraphBuilderUtils::ConnectExec(UEdGraph* Graph, UEdGraphNode* Source, const FString& SourcePinName, UEdGraphNode* Target, FBlueprintGraphBuildStats* Stats)
{
    return Link(Graph, FindPin(Source, SourcePinName, EGPD_Output), FindPin(Target, TEXT("execute"), EGPD_Input), Stats);
}

UK2Node_CallFunction* FBlueprintGraphBuilderUtils::AddFunctionCall(UEdGraph* Graph, UFunction* Function, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats, const FString& NodeComment)
{
    if (!Graph || !Function)
    {
        return nullptr;
    }

    UK2Node_CallFunction* Node = NewObject<UK2Node_CallFunction>(Graph);
    Node->SetFromFunction(Function);
    return PrepareNode(Graph, Node, PosX, PosY, Stats, NodeComment);
}

UK2Node_CallFunction* FBlueprintGraphBuilderUtils::AddSelfFunctionCall(UEdGraph* Graph, FName FunctionName, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats, const FString& NodeComment)
{
    if (!Graph)
    {
        return nullptr;
    }

    UK2Node_CallFunction* Node = NewObject<UK2Node_CallFunction>(Graph);
    Node->FunctionReference.SetSelfMember(FunctionName);
    return PrepareNode(Graph, Node, PosX, PosY, Stats, NodeComment);
}

UK2Node_VariableGet* FBlueprintGraphBuilderUtils::AddVariableGet(UEdGraph* Graph, FName VarName, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats, const FString& NodeComment)
{
    if (!Graph)
    {
        return nullptr;
    }

    UK2Node_VariableGet* Node = NewObject<UK2Node_VariableGet>(Graph);
    Node->VariableReference.SetSelfMember(VarName);
    return PrepareNode(Graph, Node, PosX, PosY, Stats, NodeComment);
}

UK2Node_VariableSet* FBlueprintGraphBuilderUtils::AddVariableSet(UEdGraph* Graph, FName VarName, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats, const FString& NodeComment)
{
    if (!Graph)
    {
        return nullptr;
    }

    UK2Node_VariableSet* Node = NewObject<UK2Node_VariableSet>(Graph);
    Node->VariableReference.SetSelfMember(VarName);
    return PrepareNode(Graph, Node, PosX, PosY, Stats, NodeComment);
}

UK2Node_IfThenElse* FBlueprintGraphBuilderUtils::AddBranch(UEdGraph* Graph, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats, const FString& NodeComment)
{
    if (!Graph)
    {
        return nullptr;
    }

    UK2Node_IfThenElse* Node = NewObject<UK2Node_IfThenElse>(Graph);
    return PrepareNode(Graph, Node, PosX, PosY, Stats, NodeComment);
}

UK2Node_DynamicCast* FBlueprintGraphBuilderUtils::AddDynamicCast(UEdGraph* Graph, UClass* TargetClass, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats, const FString& NodeComment)
{
    if (!Graph || !TargetClass)
    {
        return nullptr;
    }

    UK2Node_DynamicCast* Node = NewObject<UK2Node_DynamicCast>(Graph);
    Node->TargetType = TargetClass;
    Node->SetPurity(false);
    return PrepareNode(Graph, Node, PosX, PosY, Stats, NodeComment);
}

UK2Node_Event* FBlueprintGraphBuilderUtils::FindOrCreateActorEvent(UBlueprint* Blueprint, UEdGraph* Graph, FName EventName, int32 PosX, int32 PosY, UClass* EventOwner)
{
    if (!Blueprint || !Graph)
    {
        return nullptr;
    }

    for (UEdGraphNode* Node : Graph->Nodes)
    {
        if (UK2Node_Event* EventNode = Cast<UK2Node_Event>(Node))
        {
            if (EventNode->EventReference.GetMemberName() == EventName)
            {
                return EventNode;
            }
        }
    }

    UK2Node_Event* EventNode = NewObject<UK2Node_Event>(Graph);
    EventNode->EventReference.SetExternalMember(EventName, EventOwner ? EventOwner : AActor::StaticClass());
    EventNode->bOverrideFunction = true;
    EventNode->NodePosX = PosX;
    EventNode->NodePosY = PosY;
    EventNode->CreateNewGuid();
    Graph->AddNode(EventNode, true, false);
    EventNode->PostPlacedNewNode();
    EventNode->AllocateDefaultPins();
    return EventNode;
}

int32 FBlueprintGraphBuilderUtils::RemoveNodesWithComment(UEdGraph* Graph, const FString& NodeComment)
{
    if (!Graph)
    {
        return 0;
    }

    TArray<UEdGraphNode*> ToRemove;
    for (UEdGraphNode* Node : Graph->Nodes)
    {
        if (Node && Node->NodeComment == NodeComment)
        {
            ToRemove.Add(Node);
        }
    }

    for (UEdGraphNode* Node : ToRemove)
    {
        Node->BreakAllNodeLinks();
        Graph->RemoveNode(Node);
    }

    return ToRemove.Num();
}

bool FBlueprintGraphBuilderUtils::SetPinDefault(UEdGraphPin* Pin, const FString& Value)
{
    if (!Pin)
    {
        return false;
    }

    Pin->DefaultValue = Value;
    return true;
}

bool FBlueprintGraphBuilderUtils::SetPinDefaultObject(UEdGraphPin* Pin, UObject* Object)
{
    if (!Pin)
    {
        return false;
    }

    Pin->DefaultObject = Object;
    Pin->DefaultValue = Object ? Object->GetPathName() : FString();
    return true;
}

bool FBlueprintGraphBuilderUtils::SetPinDefaultClass(UEdGraphPin* Pin, UClass* Class)
{
    if (!Pin)
    {
        return false;
    }

    Pin->DefaultObject = Class;
    Pin->DefaultValue.Reset();
    Pin->AutogeneratedDefaultValue.Reset();
    return true;
}

bool FBlueprintGraphBuilderUtils::SetObjectPropertyValue(UObject* Object, FName PropertyName, UObject* Value, FBlueprintGraphBuildStats* Stats)
{
    if (!Object)
    {
        return false;
    }

    FObjectPropertyBase* Property = FindFProperty<FObjectPropertyBase>(Object->GetClass(), PropertyName);
    if (!Property)
    {
        AddWarning(Stats, FString::Printf(TEXT("Object property not found: %s"), *PropertyName.ToString()));
        return false;
    }

    Property->SetObjectPropertyValue_InContainer(Object, Value);
    return true;
}

bool FBlueprintGraphBuilderUtils::SetNamePropertyValue(UObject* Object, FName PropertyName, FName Value, FBlueprintGraphBuildStats* Stats)
{
    if (!Object)
    {
        return false;
    }

    FNameProperty* Property = FindFProperty<FNameProperty>(Object->GetClass(), PropertyName);
    if (!Property)
    {
        AddWarning(Stats, FString::Printf(TEXT("Name property not found: %s"), *PropertyName.ToString()));
        return false;
    }

    Property->SetPropertyValue_InContainer(Object, Value);
    return true;
}

bool FBlueprintGraphBuilderUtils::SetFloatPropertyValue(UObject* Object, FName PropertyName, double Value, FBlueprintGraphBuildStats* Stats)
{
    if (!Object)
    {
        return false;
    }

    FNumericProperty* Property = FindFProperty<FNumericProperty>(Object->GetClass(), PropertyName);
    if (!Property || !Property->IsFloatingPoint())
    {
        AddWarning(Stats, FString::Printf(TEXT("Float property not found: %s"), *PropertyName.ToString()));
        return false;
    }

    Property->SetFloatingPointPropertyValue(Property->ContainerPtrToValuePtr<void>(Object), Value);
    return true;
}

bool FBlueprintGraphBuilderUtils::SetBoolPropertyValue(UObject* Object, FName PropertyName, bool Value, FBlueprintGraphBuildStats* Stats)
{
    if (!Object)
    {
        return false;
    }

    FBoolProperty* Property = FindFProperty<FBoolProperty>(Object->GetClass(), PropertyName);
    if (!Property)
    {
        AddWarning(Stats, FString::Printf(TEXT("Bool property not found: %s"), *PropertyName.ToString()));
        return false;
    }

    Property->SetPropertyValue_InContainer(Object, Value);
    return true;
}
