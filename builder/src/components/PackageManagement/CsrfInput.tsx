import React from "react";
import { useCsrfToken } from "../CsrfTokenContext";

export const CsrfInput: React.FC = () => {
    const token = useCsrfToken();
    return <input type="hidden" name="csrfmiddlewaretoken" value={token} />;
};
