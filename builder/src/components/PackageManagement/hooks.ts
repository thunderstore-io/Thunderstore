import { useForm } from "react-hook-form";
import { ExperimentalApi, UpdatePackageListingResponse } from "../../api";
import * as Sentry from "@sentry/react";
import { useState } from "react";
import { Control } from "react-hook-form/dist/types";
import { UseFormSetValue } from "react-hook-form";

type Status = undefined | "SUBMITTING" | "SUCCESS" | "ERROR";
export type PackageListingUpdateFormValues = {
    categories: { value: string; label: string }[];
    readme?: { fileName: string; content: string };
    changelog?: { fileName: string; content: string };
};

export type PackageListingUpdateForm = {
    onSubmit: () => Promise<void>;
    setValue: UseFormSetValue<PackageListingUpdateFormValues>;
    control: Control<PackageListingUpdateFormValues>;
    error?: string;
    status: Status;
};

export const usePackageListingUpdateForm = (
    packageListingId: string,
    onSuccess: (result: UpdatePackageListingResponse) => void
): PackageListingUpdateForm => {
    const { handleSubmit, control, setValue } = useForm<PackageListingUpdateFormValues>();
    const [status, setStatus] = useState<Status>(undefined);
    const [error, setError] = useState<string | undefined>(undefined);

    const onSubmit = handleSubmit(async (data) => {
        if (status === "SUBMITTING") return;
        setError(undefined);
        setStatus("SUBMITTING");
        try {
            const result = await ExperimentalApi.updatePackageListing({
                packageListingId: packageListingId,
                data: {
                    categories: data.categories.map((x) => x.value),
                    readme: data.readme?.content,
                    changelog: data.changelog?.content,
                },
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
        setValue,
        control,
        error,
        status,
    };
};
