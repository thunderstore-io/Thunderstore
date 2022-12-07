import * as Sentry from "@sentry/react";
import React, { useState } from "react";
import { FormSelectField } from "../FormSelectField";
import { useForm } from "react-hook-form";
import { ExperimentalApi, PackageCategory } from "../../api";

type CategoriesFormProps = {
    csrfToken: string;
    canUpdateCategories: boolean;
    currentCategories: PackageCategory[];
    availableCategories: PackageCategory[];
    packageListingId: string;
};

type Status = undefined | "SUBMITTING" | "SUCCESS" | "ERROR";

export const CategoriesForm: React.FC<CategoriesFormProps> = (props) => {
    const { handleSubmit, control } = useForm();
    const [status, setStatus] = useState<Status>(undefined);
    const [error, setError] = useState<string | undefined>(undefined);

    const onSubmit = async (data: {
        categories: { value: string; label: string }[];
    }) => {
        if (status === "SUBMITTING") return;
        setError(undefined);
        setStatus("SUBMITTING");
        try {
            await ExperimentalApi.updatePackageListing({
                packageListingId: props.packageListingId,
                data: { categories: data.categories.map((x) => x.value) },
            });
            setStatus("SUCCESS");
        } catch (e) {
            Sentry.captureException(e);
            setError(`${e}`);
            setStatus("ERROR");
        }
    };

    return (
        <form onSubmit={handleSubmit(onSubmit)}>
            <FormSelectField
                control={control}
                name={"categories"}
                data={props.availableCategories}
                default={props.currentCategories}
                getOption={(x) => {
                    return {
                        value: x.slug,
                        label: x.name,
                    };
                }}
                isMulti={true}
            >
                <p className="mt-1 mb-2">
                    Note that the selected categories are applied only to the
                    current community. If you need to add categories to other
                    communities, you can do so on the site of that community.
                </p>
            </FormSelectField>
            <button
                type={"submit"}
                className="btn btn-primary btn-block"
                disabled={status === "SUBMITTING"}
            >
                Save
            </button>
            {error && (
                <div className={"alert alert-danger mt-2 mb-0"}>
                    <p className={"mb-0"}>{error}</p>
                </div>
            )}
            {status === "SUBMITTING" && (
                <div className={"alert alert-warning mt-2 mb-0"}>
                    <p className={"mb-0"}>Saving...</p>
                </div>
            )}
            {status === "SUCCESS" && (
                <div className={"alert alert-success mt-2 mb-0"}>
                    <p className={"mb-0"}>Changes saved successfully!</p>
                </div>
            )}
        </form>
    );
};
