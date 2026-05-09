import { useEffect } from "react";
import { Control, useWatch } from "react-hook-form";
import { Community } from "../api";

export const AI_GENERATED_SLUG = "ai-generated";
const AI_GENERATED_OPTION = { value: AI_GENERATED_SLUG, label: "AI Generated" };

interface CategoryOption {
    value: string;
    label: string;
}

interface CategoriesFormValues {
    [key: string]: CategoryOption[] | undefined;
}

const hasAiChip = (cats: CategoryOption[]) =>
    cats.some((c) => c.value === AI_GENERATED_SLUG);

const getAttestingIds = (
    communities: Community[] | null,
    idsKey: string
): string[] => {
    if (!communities || idsKey === "") return [];
    const selected = new Set(idsKey.split(","));
    return communities
        .filter((c) => c.require_ai_attestation && selected.has(c.identifier))
        .map((c) => c.identifier);
};

interface AiAttestationSyncOptions {
    communities: Community[] | null;
    selectedCommunityIds: string[];
    aiAnswer: string | undefined;
    setAiAnswer: (value: "yes" | "no") => void;
    categoriesControl: Control<CategoriesFormValues>;
    getCategoryValues: () => CategoriesFormValues;
    resetCategoryValues: (values: CategoriesFormValues) => void;
}

// Sync between AI attestation control and the category.
export const useAiAttestationSync = ({
    communities,
    selectedCommunityIds,
    aiAnswer,
    setAiAnswer,
    categoriesControl,
    getCategoryValues,
    resetCategoryValues,
}: AiAttestationSyncOptions): boolean => {
    const idsKey = selectedCommunityIds.join(",");
    const watchedCategoryValues = useWatch({ control: categoriesControl });

    // Propagate radio answer to chip presence in enrolled communities.
    useEffect(() => {
        const attestingIds = getAttestingIds(communities, idsKey);
        if (attestingIds.length === 0) return;
        const updated = { ...getCategoryValues() };
        let changed = false;
        for (const id of attestingIds) {
            const cats = updated[id] ?? [];
            if (aiAnswer === "yes" && !hasAiChip(cats)) {
                updated[id] = [...cats, AI_GENERATED_OPTION];
                changed = true;
            } else if (aiAnswer === "no" && hasAiChip(cats)) {
                updated[id] = cats.filter((c) => c.value !== AI_GENERATED_SLUG);
                changed = true;
            }
        }
        if (changed) resetCategoryValues(updated);
    }, [aiAnswer, idsKey, communities, getCategoryValues, resetCategoryValues]);

    // Propagate chip selection to radio answer.
    useEffect(() => {
        const attestingIds = getAttestingIds(communities, idsKey);
        if (attestingIds.length === 0) return;
        const fresh = getCategoryValues();
        const allHave = attestingIds.every((id) => hasAiChip(fresh[id] ?? []));
        const anyHave = attestingIds.some((id) => hasAiChip(fresh[id] ?? []));
        if (aiAnswer === "yes" && !allHave) {
            setAiAnswer("no");
        } else if (aiAnswer !== "yes" && anyHave) {
            setAiAnswer("yes");
        }
    }, [
        watchedCategoryValues,
        idsKey,
        communities,
        aiAnswer,
        setAiAnswer,
        getCategoryValues,
    ]);

    return getAttestingIds(communities, idsKey).length > 0;
};
