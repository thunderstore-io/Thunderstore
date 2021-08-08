import React, { useEffect, useState } from "react";
import { ExperimentalApi, ThunderstoreApiError } from "./api";
import { ProgressBar } from "./components/ProgressBar";
import { useDebounce } from "./debounce";
import * as Sentry from "@sentry/react";
import { CodeInputPanel } from "./components/CodeInputPanel";
import Select from "react-select";
import { Base64 } from "js-base64";

const LOCAL_STORAGE_KEY = "legacy.manifestValidator.manifest";
const EXAMPLE_MANIFEST = `
{
    "name": "TestMod",
    "version_number": "1.1.0",
    "website_url": "https://github.com/thunderstore-io",
    "description": "This is a description for a mod. 250 characters max",
    "dependencies": [
        "Mythic-TestMod-1.1.0"
    ]
}
`.trim();

interface ManifestV1ValidationErrors {
    non_field_errors?: string[];
}

interface ManifestValidatorProps {
    manifest: string;
    namespace: string | null;
}
const ManifestValidator: React.FC<ManifestValidatorProps> = ({
    manifest,
    namespace,
}) => {
    const [progressClass, setProgressClass] = useState<string | null>(null);
    const [validationErrors, setValidationErrors] = useState<string[]>([]);

    const validateManifest = () => {
        try {
            localStorage.setItem(LOCAL_STORAGE_KEY, manifest);
        } catch (e) {
            Sentry.captureException(e);
        }
        const errors: string[] = [];
        if (manifest.length <= 0) {
            errors.push("Enter manifest contents");
        }
        if (namespace == null) {
            errors.push(
                "Select a team. You must be logged in to see your teams."
            );
        }
        if (manifest.length > 0 && namespace != null) {
            ExperimentalApi.validateManifestV1({
                data: {
                    namespace: namespace,
                    manifest_data: Base64.encode(manifest),
                },
            })
                .then((result) => {
                    if (result.success) {
                        setProgressClass("bg-success");
                        setValidationErrors([]);
                    } else {
                        setValidationErrors(["Unknown validation error"]);
                        setProgressClass("bg-danger");
                    }
                })
                .catch((e) => {
                    if (e instanceof ThunderstoreApiError) {
                        const result = e.errorObject as ManifestV1ValidationErrors;
                        if (result.non_field_errors) {
                            errors.push(...result.non_field_errors);
                        }
                    } else {
                        errors.push(
                            "Unknown error occurred when calling the validation API"
                        );
                        Sentry.captureException(e);
                    }
                    setProgressClass("bg-danger");
                    setValidationErrors(errors);
                });
        } else {
            setProgressClass("bg-danger");
            setValidationErrors(errors);
        }
    };

    useDebounce(
        600,
        () => {
            validateManifest();
        },
        [manifest, namespace],
        () => setProgressClass("bg-warning")
    );

    return (
        <div className={"card bg-light mb-2"}>
            <div className={"card-header"}>
                {progressClass !== null ? (
                    <ProgressBar className={progressClass} progress={100} />
                ) : null}
            </div>
            <div className={"card-body markdown-body"}>
                {validationErrors.length > 0 ? (
                    <ul className={"text-danger"}>
                        {validationErrors.map((message) => (
                            <li key={message}>{message}</li>
                        ))}
                    </ul>
                ) : (
                    <p>No errors found!</p>
                )}
            </div>
        </div>
    );
};

export const ManifestValidationPage: React.FC = () => {
    const [manifest, setManifest] = useState<string>(
        localStorage.getItem(LOCAL_STORAGE_KEY) || EXAMPLE_MANIFEST
    );
    const [namespace, setNamespace] = useState<string | null>(null);
    const [namespaces, setNamespaces] = useState<string[]>([]);

    useEffect(() => {
        ExperimentalApi.currentUser().then((res) => setNamespaces(res.teams));
    }, []);

    const namespaceChoices = namespaces.map((x) => ({ value: x, label: x }));

    const handleNamespaceChange = (
        value: { value: string; label: string },
        action: { action: string }
    ) => {
        if (action.action == "set-value" || action.action == "select-option") {
            setNamespace(value.value);
        }
    };

    return (
        <div style={{ marginBottom: "96px" }}>
            <CodeInputPanel
                title={"Manifest Validator"}
                initial={manifest}
                onChange={setManifest}
                textareaStyle={{ minHeight: "300px" }}
            >
                <div className="w-100 mb-2">
                    <div style={{ color: "#666" }}>
                        <Select
                            options={namespaceChoices}
                            onChange={handleNamespaceChange as any}
                        />
                    </div>
                </div>
            </CodeInputPanel>
            <ManifestValidator manifest={manifest} namespace={namespace} />
        </div>
    );
};
