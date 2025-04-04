import { useForm } from "react-hook-form";
import { ExperimentalApi, ThunderstoreApiError } from "../../api";
import * as Sentry from "@sentry/react";
import { useState } from "react";
import { Control, FieldError } from "react-hook-form/dist/types";

type Status = undefined | "SUBMITTING" | "SUCCESS" | "ERROR";
export type ReportFormValues = {
    reason?: { label: string; value: string };
    description?: string;
};

export type ReportForm = {
    onSubmit: () => Promise<void>;
    control: Control<ReportFormValues>;
    fieldErrors?: { [key in keyof ReportFormValues]: FieldError };
    error?: string;
    status: Status;
};

export const useReportForm = (props: {
    packageListingId: string;
    packageVersionId: string;
}): ReportForm => {
    const { handleSubmit, control, formState } = useForm<ReportFormValues>();
    const [status, setStatus] = useState<Status>(undefined);
    const [error, setError] = useState<string | undefined>(undefined);

    const onSubmit = handleSubmit(async (data) => {
        if (status === "SUBMITTING") return;
        setError(undefined);
        if (!data.reason) {
            setError("Reason must be selected");
            setStatus("ERROR");
            return;
        }
        setStatus("SUBMITTING");
        try {
            await ExperimentalApi.reportPackageListing({
                packageListingId: props.packageListingId,
                data: {
                    package_version_id: props.packageVersionId,
                    reason: data.reason.value,
                    description: data.description,
                },
            });
            setStatus("SUCCESS");
        } catch (e) {
            Sentry.captureException(e);
            setStatus("ERROR");
            if (e instanceof ThunderstoreApiError && e.extractedMessage) {
                setError(e.extractedMessage);
            } else {
                setError(`${e}`);
            }
        }
    });

    return {
        onSubmit,
        control,
        // TODO: Fix types, the DeepMap type in react-hook-form doesn't seem to work for some reason
        fieldErrors: formState.errors as any,
        error,
        status,
    };
};
