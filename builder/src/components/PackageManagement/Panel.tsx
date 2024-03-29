import React, { useState } from "react";
import { ContextProps, ManagementContextProvider } from "./Context";
import { PackageManagementModal } from "./Modal";
import { CsrfTokenProvider } from "../CsrfTokenContext";

export const PackageManagementPanel: React.FC<ContextProps> = (props) => {
    const [isVisible, setIsVisible] = useState<boolean>(false);
    const closeModal = () => setIsVisible(false);

    return (
        <CsrfTokenProvider token={props.csrfToken}>
            <ManagementContextProvider initial={props} closeModal={closeModal}>
                {isVisible && <PackageManagementModal />}
                <button
                    type="button"
                    className="btn btn-primary"
                    aria-label="Manage Package"
                    onClick={() => setIsVisible(true)}
                >
                    <span className="fa fa-cog" />
                    &nbsp;&nbsp;Manage Package
                </button>
            </ManagementContextProvider>
        </CsrfTokenProvider>
    );
};
