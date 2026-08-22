# Goldhand Clinic Blog — macOS only

This repository and every release asset in it are exclusively for Apple Mac computers. It intentionally uses a separate repository, installer name, install folder, marketplace name, updater, and release archive from the Windows distribution.

## Recipient installation

1. Download `Goldhand-Clinic-Blog-Mac-Installer.zip` from the direct latest-release link.
2. Double-click the ZIP, then double-click `INSTALL-MAC.command`.
3. If macOS blocks the first launch, Control-click `INSTALL-MAC.command`, choose **Open**, and confirm **Open** once.
4. When the browser opens, sign in to the recipient's own Vercel account and approve the connection once.
5. Wait for `INSTALLATION COMPLETE`, close the Terminal window, and reopen ChatGPT.

After that one browser approval, the installer creates and links the recipient-owned image project, performs the first production deployment, selects a stable HTTPS alias, and saves the configuration outside the managed plugin folder. GPT image publication and HTML insertion then run automatically. Plugin updates do not erase this setup.

No Vercel password or token is bundled. If the browser approval is closed, `Goldhand Image Setup.command` remains on the Desktop as a retry launcher.

## macOS isolation

- Repository: `seojun03/goldhand-clinic-blog-macos`
- Installer: `INSTALL-MAC.command` inside `Goldhand-Clinic-Blog-Mac-Installer.zip`
- Managed folder: `~/GoldhandBlogMac`
- Marketplace: `goldhand-clinic-macos`
- Release archive: `goldhand-clinic-blog-macos.zip`
- Update agent: `com.goldhand.clinic-blog.macos.update`

The installer exits immediately on a non-macOS operating system and never reads, replaces, registers, or removes the Windows marketplace or managed folder.
