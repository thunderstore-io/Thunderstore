import React, { useMemo } from "react";
import { CsrfInput } from "./CsrfInput";
import { useManagementContext } from "./Context";

type Button = {
    className: string;
    name: string;
};

export const DeprecationForm: React.FC = () => {
    const context = useManagementContext().props;

    const buttons = useMemo(() => {
        const result: Button[] = [];
        if (context.canDeprecate) {
            result.push({ name: "deprecate", className: "btn-warning" });
        }
        if (context.canUndeprecate) {
            result.push({ name: "undeprecate", className: "btn-primary" });
        }
        if (context.canUnlist) {
            result.push({ name: "unlist", className: "btn-danger" });
        }
        return result;
    }, [context.canDeprecate, context.canUndeprecate, context.canUnlist]);

    return (
        <form method="POST" action="#">
            <CsrfInput />
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
