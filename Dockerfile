# First stage: Build the .NET code
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build

# Define a build argument for the version
# https://github.com/microsoft/Tools-for-Health-Data-Anonymization/releases
ARG TOOLS_FOR_HEALTH_DATA_VERSION=4.2.2

# Install wget (if not already available)
RUN apt-get update && apt-get install -y wget

# Download the source tar.gz from the GitHub releases page using the version argument
RUN wget https://github.com/microsoft/Tools-for-Health-Data-Anonymization/archive/refs/tags/v${TOOLS_FOR_HEALTH_DATA_VERSION}.tar.gz -O source.tar.gz

# Extract the tar.gz file and then remove the archive to clean up
RUN tar -xzf source.tar.gz && rm source.tar.gz

# Rename the extracted folder to 'app' using the version argument
RUN mv Tools-for-Health-Data-Anonymization-${TOOLS_FOR_HEALTH_DATA_VERSION} app

WORKDIR /app

RUN ls -halt .

RUN ls -haltR FHIR/src/

RUN sed -i 's/<TargetFramework>net[0-9.]*<\/TargetFramework>/<TargetFramework>net8.0<\/TargetFramework>/g' FHIR/src/Microsoft.Health.Fhir.Anonymizer.R4.CommandLineTool/*.csproj

# Build the project
RUN dotnet build FHIR/src/Microsoft.Health.Fhir.Anonymizer.R4.CommandLineTool -c Release -p:TargetFramework=net8.0

# Second stage: Set up the runtime environment for .NET, Mono (v6.12+), and Python
FROM mcr.microsoft.com/dotnet/runtime:8.0

# Install Python, pip, pythonnet, and Mono
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    pip install pipenv --break-system-packages

WORKDIR /app

ENV PYTHONPATH=/app;/lib/netlib
ENV PATH="/lib/netlib:${PATH}"

# Copy the build output from the first stage
COPY --from=build /app/FHIR/src/Microsoft.Health.Fhir.Anonymizer.R4.CommandLineTool/bin/Release/net8.0 /lib/netlib

RUN ls -halt /lib/netlib

ENV PYTHONNET_RUNTIME=coreclr

# Copy Pipfile and Pipfile.lock
COPY Pipfile Pipfile.lock /app/

# Install dependencies using pipenv
RUN pipenv sync --dev --system --verbose --extra-pip-args="--prefer-binary --break-system-packages"

# Copy the FastAPI Python code
COPY ./deidentifier /app/deidentifier

# add script to pass through anonymize command to dotnet
COPY ./anonymize.sh /app/anonymize.sh

RUN chmod +x /app/anonymize.sh && cp /app/anonymize.sh /usr/local/bin/anonymize

# Expose the FastAPI port
EXPOSE 8000

# Command to run FastAPI
CMD ["uvicorn", "deidentifier.main:app", "--host", "0.0.0.0", "--port", "8000"]
