import * as ReactDOM from "react-dom";
import "./js/custom";

import { UploadPage } from "./upload";
import React, { ComponentClass, FunctionComponent } from "react";

const CreateComponent = (component: FunctionComponent | ComponentClass) => {
    return (element: Element) => {
        ReactDOM.render(React.createElement(component), element);
    };
};

(window as any).ts = {
    UploadPage: CreateComponent(UploadPage),
};
