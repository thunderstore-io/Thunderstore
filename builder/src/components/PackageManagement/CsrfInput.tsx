import React from "react";

type CsrfInputProps = {
    csrfToken: string;
};
export const CsrfInput: React.FC<CsrfInputProps> = (props) => {
    return (
        <input
            type="hidden"
            name="csrfmiddlewaretoken"
            value={props.csrfToken}
        />
    );
};
