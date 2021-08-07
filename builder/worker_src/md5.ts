import * as crypto from "crypto-js";

function calculateMD5(blob: Blob): Promise<string> {
    return new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const md5 = crypto.MD5(
                crypto.enc.Latin1.parse(reader.result!.toString())
            );
            resolve(md5.toString(crypto.enc.Base64));
        };
        reader.readAsBinaryString(blob);
    });
}

onmessage = (ev) => {
    const messageId = ev.data.messageId;
    const message = ev.data.message;

    if (messageId !== undefined && message !== undefined) {
        calculateMD5(message).then((md5) => {
            const response = {
                message: md5,
                messageId: messageId,
            };
            (postMessage as any)(response);
        });
    } else {
        console.error(`Unknown worker message format: ${ev.data}`);
    }
};
