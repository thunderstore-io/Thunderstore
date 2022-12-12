import React, { useState } from "react";
import { ContextProps, ManagementContextProvider } from "./Context";
import { PackageManagementModal } from "./Modal";

export const PackageManagementPanel: React.FC<ContextProps> = (props) => {
    const [isVisible, setIsVisible] = useState<boolean>(false);
    const closeModal = () => setIsVisible(false);

    return (
        <ManagementContextProvider initial={props} closeModal={closeModal}>
            <div className="d-flex justify-content-end">
                {isVisible && <PackageManagementModal />}
                <button
                    type="button"
                    className="btn btn-primary"
                    aria-label="Manage Package"
                    onClick={() => setIsVisible(true)}
                >
                    <span className="fa fa-cog" />
                    &nbsp;Manage Package
                </button>
            </div>
        </ManagementContextProvider>
    );
};
