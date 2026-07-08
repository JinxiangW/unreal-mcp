#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class FExtractionFootprintGraphBuilder
{
public:
    static TSharedPtr<FJsonObject> SetupGraph(const TSharedPtr<FJsonObject>& Params);
};
