import React, { useState } from "react";
import { ContextProps, ReviewContextProvider } from "./Context";
import { PackageReviewModal } from "./Modal";

export const PackageReviewPanel: React.FC<ContextProps> = (props) => {
    const [isVisible, setIsVisible] = useState<boolean>(false);
    const closeModal = () => setIsVisible(false);

    return (
        <ReviewContextProvider initial={props} closeModal={closeModal}>
            {isVisible && <PackageReviewModal />}
            <button
                type="button"
                className="btn btn-warning"
                aria-label="Review Package"
                onClick={() => setIsVisible(true)}
            >
                <span className="fa fa-cog" />
                &nbsp;&nbsp;Review Package
            </button>
        </ReviewContextProvider>
    );
};
