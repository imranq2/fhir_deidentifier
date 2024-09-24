#!/bin/bash

# Run the dotnet command with all the arguments passed to the script
dotnet /lib/netlib/Microsoft.Health.Fhir.Anonymizer.R4.CommandLineTool.dll anonymize "$@"
