# Instructions de redaction du rapport PFE

## 1) Objectif de ce document
Ce document te donne une methode de redaction progressive, avec une story claire:
- ou trouver la preuve de chaque composant (UI vs code),
- quoi capturer en image,
- quels tests executer et documenter,
- dans quel chapitre inserer chaque element.

## 2) Story globale du rapport (fil narratif)
Le rapport doit raconter une progression logique:
1. Situation initiale (acces permanents, faible tracabilite, risque eleve).
2. Exigence Zero Trust (verifier identite, limiter privilege, limiter duree).
3. Choix architecture (Authentik + Tailscale ACL + Flask/PostgreSQL + moteur JIT + Wazuh).
4. Implementation composant par composant.
5. Demonstration par scenarios de test reel avant/apres autorisation.
6. Resultats mesures (metriques de reduction de surface d'attaque).
7. Limites et evolutions.

## 3) Ou prendre la preuve pour chaque composant

### Authentik (majoritairement UI)
Preuves attendues:
- configuration provider/application OIDC,
- groupes et policies,
- flow MFA/TOTP,
- ecran login ou challenge MFA.

Sources:
- UI Authentik (principal)
- fichiers de deploiement: Authentik/docker-compose.yml, scripts setup

### Tailscale ACL (UI + policy JSON)
Preuves attendues:
- configuration ACL/tags,
- policy qui autorise/refuse selon groupe/tag,
- visualisation machine cible.

Sources:
- console admin Tailscale (principal)
- extrait policy ACL (texte)

### Application Flask + PostgreSQL (UI + code)
Preuves attendues:
- page user: creation demande d'acces,
- page admin: approbation/refus,
- affichage etat pending/approved/expired,
- verification logique anti-doublon pending.

Sources:
- UI web locale
- code: web-page/app.py, web-page/models.py, web-page/templates/*

### Moteur JIT Python ACL_work (code + execution)
Preuves attendues:
- appel approve_access_request(...),
- appel revoke_access_request(...),
- script cleanup_expired_requests(...),
- execution cron ou script manuel.

Sources:
- code: web-page/ACL_work/*
- script: web-page/scripts/expire_access.py
- logs d'execution

### Wazuh (UI dashboard + logs)
Preuves attendues:
- vue dashboard alertes/logs,
- evenement lie a connexion ou action admin,
- trace de session/action utile pour audit.

Sources:
- UI Wazuh
- config wazuh-docker/single-node/config/*

## 4) Checklist chapitres a rediger

- [ ] Chapitre 1 Contexte et problematique
- [ ] Chapitre 2 Objectifs, perimetre, methodologie
- [ ] Chapitre 3 Architecture globale et choix techniques
- [ ] Chapitre 4 Implementation par composant
- [ ] Chapitre 5 Scenarios de test et validation
- [ ] Chapitre 6 Resultats et metriques
- [ ] Chapitre 7 Limites et perspectives
- [ ] Chapitre 8 Conclusion generale
- [ ] Annexes (preuves, commandes, extraits config)

## 5) Checklist images a fournir (captures ecran)

### A. IAM Authentik
- [ ] Login page Authentik
- [ ] Ecran MFA (TOTP)
- [ ] Configuration application OIDC (client)
- [ ] Groupes/roles utilises pour le controle d'acces

### B. Tailscale
- [ ] ACL policy avant modification (etat initial)
- [ ] ACL policy apres approbation JIT
- [ ] Vue machine cible + tags
- [ ] Preuve refus acces avant approbation
- [ ] Preuve acces autorise apres approbation

### C. Application web Flask
- [ ] Page user dashboard
- [ ] Formulaire demande d'acces JIT
- [ ] Message blocage si demande pending existe deja
- [ ] Page admin dashboard avec liste des demandes
- [ ] Action approve/deny sur une demande
- [ ] Vue timer/expiration cote user

### D. Moteur JIT + scripts
- [ ] Extrait code approve_access_request
- [ ] Extrait code revoke_access_request
- [ ] Extrait code cleanup_expired_requests
- [ ] Sortie execution script expiration (terminal)

### E. Wazuh / audit
- [ ] Dashboard evenement de securite
- [ ] Log authentification ou action admin
- [ ] Log de revocation a expiration

### F. Demonstration SSH (obligatoire)
- [ ] Tentative SSH avant approbation (refusee)
- [ ] Approbation admin de la demande
- [ ] Tentative SSH apres approbation (reussie)
- [ ] Tentative SSH apres expiration TTL (refusee)

## 6) Scenarios de test a raconter (story de validation)

### Scenario 1: Authentification forte
- precondition: utilisateur existe dans Authentik
- action: login + MFA
- attendu: acces valide uniquement apres 2e facteur
- preuve: captures login/MFA + event log

### Scenario 2: Demande JIT user
- precondition: user non autorise en permanent
- action: creation demande via UI
- attendu: statut pending
- preuve: capture page user + valeur en base ou table admin

### Scenario 3: Approbation admin et activation ACL
- precondition: demande pending
- action: admin approuve
- attendu: statut approved + date expiration + ACL active
- preuve: capture admin + policy ACL + log application

### Scenario 4: Acces SSH pendant fenetre JIT
- precondition: demande approved non expiree
- action: connexion SSH vers machine cible
- attendu: connexion autorisee
- preuve: terminal + event/log

### Scenario 5: Expiration automatique et revocation
- precondition: acces approved avec TTL court
- action: attendre expiration ou lancer script cleanup
- attendu: statut expired + ACL retiree + SSH refuse
- preuve: terminal cleanup + SSH refuse + logs

## 7) Nommage conseille pour les images
Format conseille:
- ch4-authentik-login.png
- ch4-authentik-mfa.png
- ch4-tailscale-acl-before.png
- ch4-tailscale-acl-after.png
- ch4-web-user-dashboard.png
- ch4-web-admin-approve.png
- ch5-ssh-before-approval.png
- ch5-ssh-after-approval.png
- ch5-ssh-after-expiration.png
- ch5-cleanup-script-output.png
- ch6-wazuh-audit-event.png

Dossier recommande:
- rapport/images/

## 8) Plan d'execution concret (ce que tu fais maintenant)
1. Completer Chapitre 1 a 3 avec le contenu de Readme.md.
2. Capturer d'abord les preuves UI (Authentik, Tailscale, Web app).
3. Ajouter ensuite les extraits de code (ACL_work, app.py).
4. Executer les scenarios SSH avant/apres/expiration et capturer.
5. Inserer metriques avant/apres en Chapitre 6.
6. Finaliser limites/perspectives/conclusion.

## 9) Ce que j'attends de toi dans le prochain envoi (scenarios)
Quand tu partages tes scenarios de test, donne pour chaque scenario:
- preconditions,
- etapes detaillees,
- resultat attendu,
- resultat observe,
- preuves associees (nom capture ou log).

Avec ca, je redigerai directement la section complete du Chapitre 5 en LaTeX.
