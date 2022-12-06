import React, { useMemo } from "react";
import { CsrfInput } from "./CsrfInput";

type Button = {
    className: string;
    name: string;
};
type DeprecationFormProps = {
    canDeprecate: boolean;
    canUndeprecate: boolean;
    canUnlist: boolean;
    csrfToken: string;
};
export const DeprecationForm: React.FC<DeprecationFormProps> = (props) => {
    const buttons = useMemo(() => {
        const result: Button[] = [];
        if (props.canDeprecate) {
            result.push({ name: "deprecate", className: "btn-warning" });
        }
        if (props.canUndeprecate) {
            result.push({ name: "undeprecate", className: "btn-primary" });
        }
        if (props.canUnlist) {
            result.push({ name: "unlist", className: "btn-danger" });
        }
        return result;
    }, [props.canDeprecate, props.canUndeprecate, props.canUnlist]);

    return (
        <form method="POST" action="#">
            <CsrfInput csrfToken={props.csrfToken} />
            {buttons.map((x) => (
                <input
                    key={x.name}
                    type="submit"
                    className={`btn ${x.className} text-capitalize mr-2`}
                    name={x.name}
                    value={x.name}
                />
            ))}
        </form>
    );
};
