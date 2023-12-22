import { useForm } from "react-hook-form";
import { ExperimentalApi } from "../../api";
import * as Sentry from "@sentry/react";
import { useCallback, useState } from "react";
import { Control } from "react-hook-form/dist/types";

type Status = undefined | "SUBMITTING" | "SUCCESS" | "ERROR";
export type PackageListingReviewFormValues = {
    rejectionReason: string;
};

export type PackageListingReviewForm = {
    approve: () => Promise<void>;
    reject: () => Promise<void>;
    control: Control<PackageListingReviewFormValues>;
    error?: string;
    status: Status;
};

export const usePackageReviewForm = (
    packageListingId: string,
    rejectionReason?: string,
    onSuccess?: () => void
): PackageListingReviewForm => {
    const { handleSubmit, control } = useForm<PackageListingReviewFormValues>({
        defaultValues: { rejectionReason },
    });
    const [status, setStatus] = useState<Status>(undefined);
    const [error, setError] = useState<string | undefined>(undefined);

    const handleState = useCallback(
        async (handler: () => Promise<any>) => {
            if (status === "SUBMITTING") return;
            setError(undefined);
            setStatus("SUBMITTING");
            try {
                await handler();
                setStatus("SUCCESS");
            } catch (e) {
                Sentry.captureException(e);
                setError(`${e}`);
                setStatus("ERROR");
            }
        },
        [setError, setStatus]
    );

    const approve = handleSubmit(async () => {
        await handleState(async () => {
            await ExperimentalApi.approvePackageListing({
                packageListingId: packageListingId,
            });
            if (onSuccess) onSuccess();
        });
    });

    const reject = handleSubmit(async (data) => {
        await handleState(async () => {
            await ExperimentalApi.rejectPackageListing({
                packageListingId: packageListingId,
                data: { rejection_reason: data.rejectionReason },
            });
            if (onSuccess) onSuccess();
        });
    });

    return {
        approve,
        reject,
        control,
        error,
        status,
    };
};
