import { useForm } from "react-hook-form";
import { ExperimentalApi, UpdatePackageListingResponse } from "../../api";
import * as Sentry from "@sentry/react";
import { useEffect, useState } from "react";
import { Control } from "react-hook-form/dist/types";

type Status = undefined | "SUBMITTING" | "SUCCESS" | "ERROR";
export type PackageListingUpdateFormValues = {
    categories: { value: string; label: string }[];
};

export type PackageListingUpdateForm = {
    onSubmit: () => Promise<void>;
    control: Control<PackageListingUpdateFormValues>;
    error?: string;
    status: Status;
};

export const usePackageListingUpdateForm = (
    packageListingId: string,
    onSuccess: (result: UpdatePackageListingResponse) => void
): PackageListingUpdateForm => {
    const { handleSubmit, control } = useForm<PackageListingUpdateFormValues>();
    const [status, setStatus] = useState<Status>(undefined);
    const [error, setError] = useState<string | undefined>(undefined);

    const onSubmit = handleSubmit(async (data) => {
        if (status === "SUBMITTING") return;
        setError(undefined);
        setStatus("SUBMITTING");
        try {
            const result = await ExperimentalApi.updatePackageListing({
                packageListingId: packageListingId,
                data: { categories: data.categories.map((x) => x.value) },
            });
            onSuccess(result);
            setStatus("SUCCESS");
        } catch (e) {
            Sentry.captureException(e);
            setError(`${e}`);
            setStatus("ERROR");
        }
    });

    return {
        onSubmit,
        control,
        error,
        status,
    };
};

export const useOnEscape = (onEscape: () => void) => {
    const handleEvent = (event: KeyboardEvent) => {
        if (event.key === "Escape") {
            onEscape();
        }
    };
    useEffect(() => {
        document.addEventListener("keydown", handleEvent);
        return () => document.removeEventListener("keydown", handleEvent);
    }, [handleEvent]);
};
