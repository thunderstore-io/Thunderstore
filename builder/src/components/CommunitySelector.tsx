import React, { useEffect, useState } from "react";
import { FormSelectField } from "./FormSelectField";
import { ExperimentalApi, PackageCategory } from "../api";
import { Control } from "react-hook-form/dist/types";
import { FormRow } from "./FormRow";

interface CategorySelectorProps {
    community: { value: string; label: string };
    control: Control;
}
const CategorySelector: React.FC<CategorySelectorProps> = ({
    community,
    control,
}) => {
    const [categories, setCategories] = useState<PackageCategory[]>([]);

    const enumerateCategories = (
        current: PackageCategory[],
        communityIdentifier: string,
        cursor?: string
    ) => {
        const promise = cursor
            ? ExperimentalApi.getNextPage<PackageCategory>(cursor)
            : ExperimentalApi.listCategories({ communityIdentifier });

        promise.then((result) => {
            // Filter out hidden categories for UI dropdown
            const visible = result.results.filter((c) => !c.hidden);
            const next = current.concat(visible);
            setCategories(next);
            if (result.pagination.next_link) {
                enumerateCategories(
                    next,
                    communityIdentifier,
                    result.pagination.next_link
                );
            }
        });
    };
    useEffect(() => {
        enumerateCategories([], community.value);
    }, [community.value]);

    const inputName = community.value;
    return (
        <FormRow
            label={community.label}
            labelFor={inputName}
            error={null}
            wrap={true}
        >
            <FormSelectField
                className={"select-category"}
                control={control}
                name={inputName}
                data={categories}
                getOption={(x) => {
                    return {
                        value: x.slug,
                        label: x.name,
                    };
                }}
                isMulti={true}
            />
        </FormRow>
    );
};

interface CommunityCategorySelectorProps {
    selectedCommunities: { value: string; label: string }[];
    control: Control;
}
export const CommunityCategorySelector: React.FC<CommunityCategorySelectorProps> = ({
    selectedCommunities,
    control,
}) => {
    if (selectedCommunities.length == 0) {
        return (
            <p className={"select-community"}>
                Select a community to view available categories
            </p>
        );
    }

    return (
        <div className={"field-row d-flex flex-column"}>
            <div className={"w-100"}>
                {selectedCommunities.map((x) => {
                    return (
                        <CategorySelector
                            key={x.value}
                            community={x}
                            control={control}
                        />
                    );
                })}
            </div>
        </div>
    );
};
