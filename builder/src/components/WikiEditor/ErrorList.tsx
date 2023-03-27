import React from "react";

export interface ErrorListProps {
    errors?: string[];
}
export const ErrorList: React.FC<ErrorListProps> = ({ errors }) => {
    if (!errors || errors.length == 0) return null;
    if (errors.length == 1) {
        return (
            <div className={"text-danger"}>
                <span>{errors[0]}</span>
            </div>
        );
    }
    return (
        <div className={"text-danger"}>
            <ul>
                {errors.map((x, i) => (
                    <li key={i}>{x}</li>
                ))}
            </ul>
        </div>
    );
};
