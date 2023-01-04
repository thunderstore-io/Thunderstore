import React from "react";

interface FormRowProps {
    label: string;
    labelFor: string;
    error: string | null;
    wrap?: boolean;
}

export const FormRow: React.FC<FormRowProps> = (props) => {
    return (
        <div className="field-wrapper">
            <div className={`field-row ${props.wrap ? "flex-wrap" : ""}`}>
                <label htmlFor={props.labelFor}>{props.label}</label>
                {props.children}
            </div>
            {props.error && (
                <div className="text-danger field-errors">{props.error}</div>
            )}
        </div>
    );
};
