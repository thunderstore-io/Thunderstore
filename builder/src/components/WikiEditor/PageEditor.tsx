import React, { useState } from "react";
import { MarkdownContextProvider } from "./MarkdownContext";
import { MarkdownPreview } from "./MarkdownPreview";
import { MarkdownEditorInput } from "./EditorInput";

interface TabProps {
    isActive?: boolean;
    title: string;
    onClick: () => void;
}
const Tab: React.FC<TabProps> = ({ isActive, title, onClick }) => {
    return (
        <li className="nav-item" role="presentation">
            <a
                className={`nav-link clickable ${isActive ? "active" : ""}`}
                style={{ userSelect: "none" }}
                aria-selected={isActive}
                role="tab"
                onClick={onClick}
            >
                {title}
            </a>
        </li>
    );
};

interface TabDef {
    title: string;
    component: React.ReactNode;
}

type TabGeneric = { [key: string]: TabDef };
interface TabsProps<T extends TabGeneric> {
    tabs: T;
    initialTab: keyof T;
}
function Tabs<T extends TabGeneric>(props: TabsProps<T>) {
    const [activeTab, setActiveTab] = useState<keyof T>(props.initialTab);

    return (
        <div>
            <ul className={"nav nav-tabs nav-secondary px-2"} role="tablist">
                {Object.entries(props.tabs).map(([key, val]) => (
                    <Tab
                        key={key}
                        isActive={activeTab == key}
                        title={val.title}
                        onClick={() => setActiveTab(key)}
                    />
                ))}
            </ul>
            <div
                className={"tab-content modal-body bg-secondary d-flex"}
                style={{ minHeight: 400, position: "relative" }}
            >
                {Object.entries(props.tabs).map(([key, val]) => (
                    <div
                        key={key}
                        className={`tab-pane fade ${
                            activeTab == key ? "active show" : ""
                        }`}
                        style={{ flex: 1 }}
                        role="tabpanel"
                    >
                        {val.component}
                    </div>
                ))}
            </div>
        </div>
    );
}

const EditorTabs: React.FC = () => {
    const tabDefs: TabGeneric = {
        write: {
            title: "Write",
            component: <MarkdownEditorInput />,
        },
        preview: {
            title: "Preview",
            component: <MarkdownPreview />,
        },
    };

    return <Tabs tabs={tabDefs} initialTab={"write"} />;
};

const PageMeta: React.FC = () => {
    return (
        <input
            className={"w-100 h5 py-1 px-2"}
            name={"title"}
            placeholder={"Title"}
        />
    );
};

const PageActions: React.FC = () => {
    return (
        <div className="modal-footer d-flex justify-content-end">
            <button
                type="button"
                className="btn btn-success"
                // disabled={props.form.status === "SUBMITTING"}
                // onClick={props.form.onSubmit}
            >
                Save
            </button>
        </div>
    );
};

export const PageEditPage: React.FC = () => {
    return (
        <MarkdownContextProvider initial={"# Test"}>
            <div className={"d-flex flex-column bg-light card"}>
                <div className={"modal-header"}>
                    <h4 className={"mb-0"}>Edit page</h4>
                </div>
                <div className={"modal-body"}>
                    <PageMeta />
                </div>
                <EditorTabs />
                <PageActions />
            </div>
        </MarkdownContextProvider>
    );
};
