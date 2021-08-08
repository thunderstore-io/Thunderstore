import * as ReactDOM from "react-dom";
import "./js/custom";

import { UploadPage } from "./upload";
import React, { ComponentClass, FunctionComponent } from "react";
import * as Sentry from "@sentry/react";
import { MarkdownPreviewPage } from "./markdown";

Sentry.init({
    // TODO: Add as a build variable instead
    dsn:
        "https://8315f0c1db2d4a538ce811f675c192c0@o578525.ingest.sentry.io/5897080",
    // TODO: Add release information
    autoSessionTracking: true,
    allowUrls: [window.location.origin],
});

const CreateComponent = (component: FunctionComponent | ComponentClass) => {
    return (element: Element) => {
        ReactDOM.render(React.createElement(component), element);
    };
};

(window as any).ts = {
    UploadPage: CreateComponent(UploadPage),
    MarkdownPreviewPage: CreateComponent(MarkdownPreviewPage),
};
