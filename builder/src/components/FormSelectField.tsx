import { Control } from "react-hook-form/dist/types";
import React, { useMemo } from "react";
import { Controller } from "react-hook-form";
import Select from "react-select";

interface FormSelectFieldProps<T, F> {
    control: Control<F>;
    name: string;
    data: T[];
    getOption: (t: T) => { value: string; label: string };
    default?: T | T[];
    isMulti?: boolean;
}
export const FormSelectField: React.FC<FormSelectFieldProps<any, any>> = (
    props
) => {
    const defaultValue = useMemo(() => {
        if (!props.default) return undefined;
        if (props.isMulti) {
            const list = Array.isArray(props.default)
                ? props.default
                : [props.default];
            return list.map(props.getOption);
        } else {
            return props.getOption(props.default);
        }
    }, [props.default, props.getOption, props.isMulti]);

    return (
        <div className="w-100">
            <div style={{ color: "#666" }}>
                <Controller
                    name={props.name}
                    control={props.control}
                    defaultValue={defaultValue}
                    render={({ field }) => (
                        <Select
                            {...field}
                            isMulti={props.isMulti || false}
                            defaultValue={defaultValue}
                            options={props.data.map(props.getOption)}
                        />
                    )}
                />
            </div>
            {props.children}
        </div>
    );
};
