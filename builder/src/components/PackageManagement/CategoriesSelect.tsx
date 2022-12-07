import React from "react";
import { FormSelectField } from "../FormSelectField";
import { PackageListingUpdateForm } from "./hooks";
import { useManagementContext } from "./Context";

type CategoriesFormProps = {
    form: PackageListingUpdateForm;
};

export const CategoriesSelect: React.FC<CategoriesFormProps> = (props) => {
    const context = useManagementContext().props;

    return (
        <FormSelectField
            control={props.form.control}
            name={"categories"}
            data={context.availableCategories}
            default={context.currentCategories}
            getOption={(x) => {
                return {
                    value: x.slug,
                    label: x.name,
                };
            }}
            isMulti={true}
        />
    );
};
