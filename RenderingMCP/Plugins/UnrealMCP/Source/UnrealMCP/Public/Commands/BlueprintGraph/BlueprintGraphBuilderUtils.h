#pragma once

#include "CoreMinimal.h"
#include "EdGraph/EdGraphPin.h"
#include "Engine/Blueprint.h"

class UK2Node_CallFunction;
class UK2Node_DynamicCast;
class UK2Node_Event;
class UK2Node_FunctionEntry;
class UK2Node_IfThenElse;
class UK2Node_VariableGet;
class UK2Node_VariableSet;
class UEdGraph;
class UEdGraphNode;
class UFunction;

struct FBlueprintGraphBuildStats
{
    int32 NodesCreated = 0;
    int32 NodesRemoved = 0;
    int32 VariablesAdded = 0;
    int32 VariablesUpdated = 0;
    TArray<FString> Warnings;
};

class FBlueprintGraphBuilderUtils
{
public:
    static FEdGraphPinType MakeObjectPin(UClass* Class);
    static FEdGraphPinType MakeBoolPin();
    static FEdGraphPinType MakeNamePin();
    static FEdGraphPinType MakeFloatPin();

    static bool SamePinType(const FEdGraphPinType& A, const FEdGraphPinType& B);
    static bool EnsureVariable(UBlueprint* Blueprint, FName VarName, const FEdGraphPinType& VarType, const FString& Category, bool bInstanceEditable, const FString& DefaultValue, FBlueprintGraphBuildStats* Stats = nullptr);

    static UEdGraph* FindFunctionGraph(UBlueprint* Blueprint, FName FunctionName);
    static UEdGraph* RecreateFunctionGraph(UBlueprint* Blueprint, FName FunctionName);
    static UK2Node_FunctionEntry* FindFunctionEntry(UEdGraph* Graph);

    static UEdGraphPin* FindPin(UEdGraphNode* Node, const FString& PinName, EEdGraphPinDirection Direction = EGPD_MAX);
    static bool Link(UEdGraph* Graph, UEdGraphPin* Source, UEdGraphPin* Target, FBlueprintGraphBuildStats* Stats = nullptr);
    static bool ConnectExec(UEdGraph* Graph, UEdGraphNode* Source, const FString& SourcePinName, UEdGraphNode* Target, FBlueprintGraphBuildStats* Stats = nullptr);

    static UK2Node_CallFunction* AddFunctionCall(UEdGraph* Graph, UFunction* Function, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats = nullptr, const FString& NodeComment = FString());
    static UK2Node_CallFunction* AddSelfFunctionCall(UEdGraph* Graph, FName FunctionName, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats = nullptr, const FString& NodeComment = FString());
    static UK2Node_VariableGet* AddVariableGet(UEdGraph* Graph, FName VarName, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats = nullptr, const FString& NodeComment = FString());
    static UK2Node_VariableSet* AddVariableSet(UEdGraph* Graph, FName VarName, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats = nullptr, const FString& NodeComment = FString());
    static UK2Node_IfThenElse* AddBranch(UEdGraph* Graph, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats = nullptr, const FString& NodeComment = FString());
    static UK2Node_DynamicCast* AddDynamicCast(UEdGraph* Graph, UClass* TargetClass, int32 PosX, int32 PosY, FBlueprintGraphBuildStats* Stats = nullptr, const FString& NodeComment = FString());
    static UK2Node_Event* FindOrCreateActorEvent(UBlueprint* Blueprint, UEdGraph* Graph, FName EventName, int32 PosX, int32 PosY, UClass* EventOwner = nullptr);

    static int32 RemoveNodesWithComment(UEdGraph* Graph, const FString& NodeComment);

    static bool SetPinDefault(UEdGraphPin* Pin, const FString& Value);
    static bool SetPinDefaultObject(UEdGraphPin* Pin, UObject* Object);
    static bool SetPinDefaultClass(UEdGraphPin* Pin, UClass* Class);

    static bool SetObjectPropertyValue(UObject* Object, FName PropertyName, UObject* Value, FBlueprintGraphBuildStats* Stats = nullptr);
    static bool SetNamePropertyValue(UObject* Object, FName PropertyName, FName Value, FBlueprintGraphBuildStats* Stats = nullptr);
    static bool SetFloatPropertyValue(UObject* Object, FName PropertyName, double Value, FBlueprintGraphBuildStats* Stats = nullptr);
    static bool SetBoolPropertyValue(UObject* Object, FName PropertyName, bool Value, FBlueprintGraphBuildStats* Stats = nullptr);
};
