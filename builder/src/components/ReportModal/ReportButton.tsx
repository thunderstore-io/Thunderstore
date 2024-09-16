import React, { useState } from "react";
import { ReportModal } from "./ReportModal";
import {
    ReportModalContextProps,
    ReportModalContextProvider,
} from "./ReportModalContext";
import { CsrfTokenProvider } from "../CsrfTokenContext";

export const ReportButton: React.FC<ReportModalContextProps> = (props) => {
    const [isVisible, setIsVisible] = useState<boolean>(false);
    const closeModal = () => setIsVisible(false);

    return (
        <CsrfTokenProvider token={props.csrfToken}>
            <ReportModalContextProvider initial={props} closeModal={closeModal}>
                {isVisible && <ReportModal />}
                <button
                    type={"button"}
                    className="btn btn-danger"
                    aria-label="Report"
                    onClick={() => setIsVisible(true)}
                >
                    <span className="fa fa-exclamation-circle" />
                    &nbsp;&nbsp;Report
                </button>
            </ReportModalContextProvider>
        </CsrfTokenProvider>
    );
};
