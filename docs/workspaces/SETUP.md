# Setting up the two workspaces

## 1. Repository (once)
1. Create a private GitHub repo `kharcha` and push this kit to `main`.
2. Protect `main`: pull requests required, CI must pass.
3. Branch prefixes: `app/T-xx-topic`, `be/T-xx-topic`, `contract/topic`, `ops/topic`.

## 2. kh-core — BACKEND workspace and backend host (one VM)
Create the VM and security rules first (PRD §24: A1.Flex 2 OCPU / 12 GB, Ubuntu 24.04 aarch64; ingress 22 from your IP, 80/443 from anywhere).
```bash
# from the laptop: copy and run the bootstrap script
scp deploy/scripts/bootstrap_server.sh ubuntu@<kh-core-public-ip>:~
ssh ubuntu@<kh-core-public-ip> 'bash ~/bootstrap_server.sh'
ssh ubuntu@<kh-core-public-ip>
claude --version && claude                             # first run: complete the login link in your laptop browser
ssh-keygen -t ed25519 -C kh-core && cat ~/.ssh/id_ed25519.pub   # add to GitHub
# dev checkout (Claude Code works here)
git clone git@github.com:<you>/kharcha.git ~/kharcha && cd ~/kharcha
git sparse-checkout set --no-cone '/*' '!/android/'    # optional: hide the Android app
cp .env.dev.example .env.dev && chmod 600 .env.dev
cp docs/workspaces/CLAUDE.local.BACKEND.md CLAUDE.local.md
# release checkout (hosted stack)
git clone git@github.com:<you>/kharcha.git /opt/kharcha
cp /opt/kharcha/.env.example /opt/kharcha/.env && chmod 600 /opt/kharcha/.env   # fill DOMAIN, passwords, NVIDIA_API_KEY
make infra-up                                          # postgres, redis (more services as tasks land)
```
## 3. Laptop — APP workspace
```bash
# Android SDK (Android Studio or command-line tools), JDK 17, Node.js 22 LTS (via nvm; Prism needs >= 20), Git, Claude Code CLI
git clone git@github.com:<you>/kharcha.git && cd kharcha
git sparse-checkout set --no-cone '/*' '!/backend/' '!/forensics/' '!/mock-erp/' '!/gateway/' '!/eval/'   # optional
cp docs/workspaces/CLAUDE.local.APP.md CLAUDE.local.md
cat scripts/ssh_config.example >> ~/.ssh/config         # set the kh-core IP
./scripts/mock-api.sh                                   # check http://localhost:4010/v1/healthz
```
