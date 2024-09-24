import json
from typing import Dict, Any

from fastapi import FastAPI, HTTPException

from deidentifier.dot_net_initializer import DotNetInitializer

app = FastAPI()


DotNetInitializer.initialize_anonymizer()

# These should come after the DotNetInitializer.initialize_anonymizer() call
# noinspection PyUnresolvedReferences
from Microsoft.Health.Fhir.Anonymizer.Core import AnonymizerConfigurationManager
# noinspection PyUnresolvedReferences
from Microsoft.Health.Fhir.Anonymizer.Core import AnonymizerEngine

@app.post("/anonymize")
async def anonymize(config: Dict[str, Any], resource: Dict[str,Any]):
    try:
        assert config
        assert isinstance(config, dict)
        assert resource
        assert isinstance(resource, dict)
        config_json = json.dumps(config)
        json_content = json.dumps(resource)
        anonymizer_configuration_manager = AnonymizerConfigurationManager.CreateFromSettingsInJson(config_json)
        result: str = AnonymizerEngine(anonymizer_configuration_manager).AnonymizeJson(json_content)
        print(result)

        return json.loads(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "Healthy"}
