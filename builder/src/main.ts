import * as ReactDOM from "react-dom";
import "./js/custom";

import { UploadPage } from "./upload";
import React, { ComponentClass, FunctionComponent } from "react";
import * as Sentry from "@sentry/react";
import { MarkdownPreviewPage } from "./markdown";
import { ManifestValidationPage } from "./manifest";
import { PackageManagementPanel } from "./components/PackageManagement/Panel";
import { PageEditPage } from "./components/WikiEditor/PageEditor";
import { PackageReviewPanel } from "./components/PackageReview/Panel";
import { ReportButton } from "./components/ReportModal/ReportButton";

Sentry.init({
    // TODO: Add as a build variable instead
    dsn:
        "https://8315f0c1db2d4a538ce811f675c192c0@o578525.ingest.sentry.io/5897080",
    // TODO: Add release information
    autoSessionTracking: true,
    allowUrls: [window.location.origin],
});

const CreateComponent = (
    component: FunctionComponent<any> | ComponentClass
) => {
    return (element: Element, encodedProps?: string) => {
        let props: any = undefined;
        if (encodedProps) {
            props = JSON.parse(atob(encodedProps));
        }
        ReactDOM.render(React.createElement(component, props), element);
    };
};

(window as any).ts = {
    UploadPage: CreateComponent(UploadPage),
    MarkdownPreviewPage: CreateComponent(MarkdownPreviewPage),
    ManifestValidationPage: CreateComponent(ManifestValidationPage),
    PackageManagementPanel: CreateComponent(PackageManagementPanel),
    PackageReviewPanel: CreateComponent(PackageReviewPanel),
    ReportButton: CreateComponent(ReportButton),
    PageEditPage: CreateComponent(PageEditPage),
};
