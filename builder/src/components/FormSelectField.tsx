import { Control } from "react-hook-form/dist/types";
import React from "react";
import { Controller } from "react-hook-form";
import Select from "react-select";

interface FormSelectFieldProps<T> {
    control: Control;
    name: string;
    data: T[];
    getOption: (t: T) => { value: string; label: string };
    default?: T;
    isMulti?: boolean;
}
export const FormSelectField: React.FC<FormSelectFieldProps<any>> = (props) => {
    const defaultValue = props.default
        ? props.isMulti
            ? [props.getOption(props.default)]
            : props.getOption(props.default)
        : undefined;

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
