import { FormErrors } from "./upload";
import { BlobReader, ZipReader } from "./vendor/zip-fs-full";

export async function validateZip(
    file: File
): Promise<{ errors: FormErrors; blockUpload: boolean }> {
    let errors = new FormErrors();

    let blockUpload = false;

    if (!file.name.toLowerCase().endsWith(".zip")) {
        errors.fileErrors.push("The file you selected is not a .zip!");
        blockUpload = true;
        return { errors, blockUpload };
    }

    if (file.name.toLowerCase().includes("test")) {
        errors.fileErrors.push(
            "If you need to test your mod, you can import it locally through the 'Import local mod' option in your mod manager's settings."
        );
    }

    try {
        const blobReader = new BlobReader(file);
        const zipReader = new ZipReader(blobReader);

        const entries = await zipReader.getEntries();

        let dllCount = 0;
        let hasBepInEx = false;
        let hasAssemblyCSharp = false;
        let maybeModpack = false;
        let rootManifest = false;
        let hasIcon = false;
        let rootIcon = false;
        let hasManifest = false;
        let hasReadMe = false;
        let rootReadMe = false;
        let wrongCase = false;
        let wrongExtension = false;
        let noExtension = false;
        for (const entry of entries) {
            console.log(entry.filename);
            if (!entry || !(typeof entry.getData === "function")) {
                continue;
            }

            if (entry.filename.toLowerCase().endsWith(".dll")) {
                dllCount++;
            }

            if (
                entry.filename.toLowerCase().split("/").pop() ==
                "assembly-csharp.dll"
            ) {
                hasAssemblyCSharp = true;
            }

            if (
                entry.filename.toLowerCase().split("/").pop() == "bepinex.dll"
            ) {
                hasBepInEx = true;
                maybeModpack = true;
            }

            if (entry.filename.toLowerCase().endsWith("manifest.json")) {
                hasManifest = true;
                if (entry.filename == "manifest.json") {
                    rootManifest = true;
                } else if (entry.filename.toLowerCase() == "manifest.json") {
                    wrongCase = true;
                    rootManifest = true;
                }
            }
            if (entry.filename.toLowerCase().endsWith("icon.png")) {
                hasIcon = true;
                if (entry.filename == "icon.png") {
                    rootIcon = true;
                } else if (entry.filename.toLowerCase() == "icon.png") {
                    wrongCase = true;
                    rootIcon = true;
                }
            }
            if (entry.filename.toLowerCase().endsWith("readme.md")) {
                hasReadMe = true;
                if (entry.filename == "README.md") {
                    rootReadMe = true;
                } else if (entry.filename.toLowerCase() == "readme.md") {
                    wrongCase = true;
                    rootReadMe = true;
                }
            }

            if (
                entry.filename.toLowerCase() == "readme.txt" ||
                entry.filename.toLowerCase() == "manifest.txt" ||
                entry.filename.toLowerCase() == "icon.jpg" ||
                entry.filename.toLowerCase() == "icon.jpeg"
            ) {
                wrongExtension = true;
            }

            if (
                entry.filename.toLowerCase() == "readme" ||
                entry.filename.toLowerCase() == "manifest" ||
                entry.filename.toLowerCase() == "icon"
            ) {
                noExtension = true;
            }
        }

        if (hasBepInEx) {
            errors.fileErrors.push(
                "You have BepInEx.dll in your .zip file. BepInEx should probably be a dependency in your manifest.json file instead."
            );
        }

        if (hasAssemblyCSharp) {
            errors.fileErrors.push(
                "You have Assembly-CSharp.dll in your .zip file. Your package may be removed if you do not have permission to distribute this file."
            );
        }

        if (dllCount > 8) {
            errors.fileErrors.push(
                "You have " +
                    dllCount +
                    " .dll files in your .zip file. Some of these files may be unnecessary."
            );
            maybeModpack = true;
        }

        if (maybeModpack) {
            errors.fileErrors.push(
                "If you're making a modpack, do not include the files for each mod in your .zip file. Instead, put the dependency string for each mod inside your manifest.json file."
            );
        }

        if (wrongCase) {
            blockUpload = true;
            errors.fileErrors.push(
                "The file names of manifest.json, icon.png, and README.md are case-sensitive."
            );
        }

        if (wrongExtension) {
            blockUpload = true;
            errors.fileErrors.push(
                "Your manifest.json, icon.png, and README.md files must have the correct file extensions."
            );
        }

        if (
            hasManifest &&
            hasIcon &&
            hasReadMe &&
            !rootManifest &&
            !rootIcon &&
            !rootReadMe
        ) {
            blockUpload = true;
            errors.fileErrors.push(
                "Your manifest, icon, and README files should be at the root of the .zip file. You can prevent this by compressing the contents of a folder, rather than the folder itself."
            );
        } else {
            if ((!hasManifest || !hasIcon || !hasReadMe) && noExtension) {
                blockUpload = true;
                errors.fileErrors.push(
                    "Your manifest.json, icon.png, or README.md file is missing its file extension."
                );
            }

            if (!hasManifest) {
                blockUpload = true;
                errors.fileErrors.push(
                    "Your package is missing a manifest.json file!"
                );
            }

            if (!hasIcon) {
                blockUpload = true;
                errors.fileErrors.push(
                    "Your package is missing an icon.png file!"
                );
            }

            if (!hasReadMe) {
                blockUpload = true;
                errors.fileErrors.push(
                    "Your package is missing a README.md file!"
                );
            }
        }

        await zipReader.close();
    } catch (e) {
        blockUpload = true;
        errors = new FormErrors();
        errors.fileErrors.push("Your .zip file could not be read.");
    }

    return { errors, blockUpload };
}
