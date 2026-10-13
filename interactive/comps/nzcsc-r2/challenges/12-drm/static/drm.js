const DRM_KEY = "6fc7b68334fd280c8a244ef439b57028";

async function deriveKey() {
    const data = new TextEncoder().encode(DRM_KEY.split("").reverse().join("") + ":DRM");
    const hash = await crypto.subtle.digest("SHA-256", data);
    return crypto.subtle.importKey("raw", hash.slice(0, 16), { name: "AES-CTR" }, false, ["encrypt", "decrypt"]);
}

async function DRM(bytes) {

    const key = await deriveKey();
    const counter = new Uint8Array([0x4e, 0x5a, 0x43, 0x53, 0x43, 0x2d, 0x44, 0x52, 0x4d, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]);
    return new Uint8Array(await crypto.subtle.decrypt({name: "AES-CTR", counter, length: 64}, key, bytes));

}