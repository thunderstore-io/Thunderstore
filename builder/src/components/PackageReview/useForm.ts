import { useForm } from "react-hook-form";
import { ExperimentalApi } from "../../api";
import * as Sentry from "@sentry/react";
import { useCallback, useState } from "react";
import { Control } from "react-hook-form/dist/types";

type Status = undefined | "SUBMITTING" | "SUCCESS" | "ERROR";
export type PackageListingReviewFormValues = {
    rejectionReason: string;
    internalNotes: string;
};

export type PackageListingReviewForm = {
    approve: () => Promise<void>;
    reject: () => Promise<void>;
    control: Control<PackageListingReviewFormValues>;
    error?: string;
    status: Status;
};

export const usePackageReviewForm = (props: {
    packageListingId: string;
    rejectionReason?: string;
    internalNotes?: string;
    onSuccess?: () => void;
}): PackageListingReviewForm => {
    const { packageListingId, rejectionReason, internalNotes } = props;

    const { handleSubmit, control } = useForm<PackageListingReviewFormValues>({
        defaultValues: {
            rejectionReason,
            internalNotes,
        },
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

    const approve = handleSubmit(async (data) => {
        await handleState(async () => {
            await ExperimentalApi.approvePackageListing({
                packageListingId: packageListingId,
                data: {
                    internal_notes: data.internalNotes,
                },
            });
            if (props.onSuccess) props.onSuccess();
        });
    });

    const reject = handleSubmit(async (data) => {
        await handleState(async () => {
            await ExperimentalApi.rejectPackageListing({
                packageListingId: packageListingId,
                data: {
                    rejection_reason: data.rejectionReason,
                    internal_notes: data.internalNotes,
                },
            });
            if (props.onSuccess) props.onSuccess();
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
