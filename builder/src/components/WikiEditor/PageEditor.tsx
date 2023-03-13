import React, { useCallback, useMemo, useState } from "react";
import { MarkdownPreview } from "./MarkdownPreview";
import { MarkdownEditorInput } from "./EditorInput";
import { useWikiEditContext, WikiEditContextProvider } from "./WikiEditContext";
import { ExperimentalApi, WikiPageUpsertRequest } from "../../api";

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
        <input
            className={"w-100 h5 py-1 px-2"}
            name={"title"}
            placeholder={"Title"}
            value={context.page.title}
            onChange={(evt) => context.setTitle(evt.target.value)}
        />
    );
};

interface PageActionsProps {
    wikiUrl: string;
}
const FooterActions: React.FC<PageActionsProps> = ({ wikiUrl }) => {
    const context = useWikiEditContext();
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

    const submit = useCallback(
        (
            data: WikiPageUpsertRequest,
            pkg: { namespace: string; name: string }
        ) => {
            if (isSubmitting) return;
            setIsSubmitting(true);
            ExperimentalApi.upsertPackageWikiPage({
                namespace: pkg.namespace,
                name: pkg.name,
                data,
            })
                .then((resp) => {
                    context.clearCache();
                    window.location.replace(`${wikiUrl}${resp.slug}/`);
                })
                .finally(() => setIsSubmitting(false));
        },
        [isSubmitting, setIsSubmitting]
    );

    const cancelUrl = useMemo(() => {
        if (context.page.id) {
            return `${wikiUrl}${context.page.id}/`;
        } else {
            return wikiUrl;
        }
    }, [wikiUrl]);

    return (
        <div className="modal-footer d-flex justify-content-end">
            <a type="button" className="btn btn-outline-dark" href={cancelUrl}>
                Cancel
            </a>
            <button
                className="btn btn-success"
                disabled={isSubmitting}
                onClick={() => submit(context.page, context.package)}
            >
                Save
            </button>
        </div>
    );
};

const HeaderActions: React.FC<PageActionsProps> = ({ wikiUrl }) => {
    const context = useWikiEditContext();
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

    const deletePage = useCallback(
        (pageId: string, pkg: { namespace: string; name: string }) => {
            if (
                !confirm(
                    "You're about to delete a page, this action can't be undone. Are you sure?"
                )
            )
                return;
            if (isSubmitting) return;
            setIsSubmitting(true);
            ExperimentalApi.deletePackageWikiPage({
                namespace: pkg.namespace,
                name: pkg.name,
                pageId,
            })
                .then(() => {
                    window.location.replace(`${wikiUrl}`);
                })
                .finally(() => setIsSubmitting(false));
        },
        [isSubmitting, setIsSubmitting]
    );

    const newPage = () => {
        window.location.replace(`${wikiUrl}new/`);
    };

    return (
        <>
            {context.page.id && (
                <button
                    className="btn btn-danger"
                    disabled={isSubmitting}
                    onClick={() =>
                        deletePage(context.page.id!, context.package)
                    }
                >
                    Delete page
                </button>
            )}
            <button
                className="btn btn-success"
                disabled={isSubmitting}
                onClick={newPage}
            >
                New page
            </button>
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
    page: WikiPageUpsertRequest | null;
    wikiUrl: string;
};

export const PageEditPage: React.FC<PageEditProps> = (props) => {
    return (
        <WikiEditContextProvider page={props.page} pkg={props.package}>
            <div className="card-header d-flex justify-content-between gap-1 flex-wrap">
                <div className="mb-0 d-flex flex-column flex-grow-1 justify-content-center">
                    <h4 className={"mb-0"}>{props.editorTitle}</h4>
                </div>
                <div className="d-flex gap-2 justify-content-end align-items-center">
                    <HeaderActions wikiUrl={props.wikiUrl} />
                </div>
            </div>
            <div className={"modal-body"}>
                <PageMeta />
            </div>
            <EditorTabs />
            <FooterActions wikiUrl={props.wikiUrl} />
        </WikiEditContextProvider>
    );
};
