import React, { useMemo, useState } from "react";
import { MarkdownPreview } from "./MarkdownPreview";
import { MarkdownEditorInput } from "./EditorInput";
import { useWikiEditContext, WikiEditContextProvider } from "./WikiEditContext";
import { WikiPageUpsertRequest } from "../../api";
import { ErrorList } from "./ErrorList";
import { LoadingIndicator } from "./LoadingIndicator";

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
    const context = useWikiEditContext();

    return (
        <>
            <input
                className={"w-100 h5 py-1 px-2"}
                name={"title"}
                placeholder={"Title"}
                value={context.page.title}
                onChange={(evt) => context.setTitle(evt.target.value)}
            />
            <ErrorList errors={context.errors?.fields.title} />
        </>
    );
};

const FooterActions: React.FC = () => {
    const context = useWikiEditContext();

    const cancelUrl = useMemo(() => {
        if (context.page.id) {
            return `${context.wikiUrl}${context.page.id}/`;
        } else {
            return context.wikiUrl;
        }
    }, [context.wikiUrl]);

    return (
        <div className="modal-footer d-flex justify-content-end">
            <ErrorList errors={context.errors?.general} />
            <a type="button" className="btn btn-outline-dark" href={cancelUrl}>
                Cancel
            </a>
            <button
                className="btn btn-success"
                disabled={context.isSubmitting}
                onClick={context.upsertPage}
            >
                Save
            </button>
        </div>
    );
};

const HeaderActions: React.FC = () => {
    const context = useWikiEditContext();

    const newPage = () => {
        window.location.replace(`${context.wikiUrl}new/`);
    };

    return (
        <>
            {context.deletePage && (
                <button
                    className="btn btn-danger"
                    disabled={context.isSubmitting}
                    onClick={context.deletePage}
                >
                    Delete page
                </button>
            )}
            <button
                className="btn btn-success"
                disabled={context.isSubmitting}
                onClick={newPage}
            >
                New page
            </button>
        </>
    );
};

export const PageEditForm: React.FC<{ title: string }> = ({ title }) => {
    const context = useWikiEditContext();

    return (
        <>
            {context.isSubmitting && <LoadingIndicator />}
            <div className="card-header d-flex justify-content-between gap-1 flex-wrap">
                <div className="mb-0 d-flex flex-column flex-grow-1 justify-content-center">
                    <h4 className={"mb-0"}>{title}</h4>
                </div>
                <div className="d-flex gap-2 justify-content-end align-items-center">
                    <HeaderActions />
                </div>
            </div>
            <div className={"modal-body"}>
                <PageMeta />
            </div>
            <EditorTabs />
            <FooterActions />
        </>
    );
};

export type PageEditProps = {
    editorTitle: string;
    csrfToken: string;
    package: {
        namespace: string;
        name: string;
    };
    options: {
        titleMaxLength: number;
        markdownMaxLength: number;
    };
    page: WikiPageUpsertRequest | null;
    wikiUrl: string;
};

export const PageEditPage: React.FC<PageEditProps> = (props) => {
    return (
        <WikiEditContextProvider
            page={props.page}
            pkg={props.package}
            options={props.options}
            wikiUrl={props.wikiUrl}
        >
            <PageEditForm title={props.editorTitle} />
        </WikiEditContextProvider>
    );
};
