@echo off

echo Compilation de : SBIHI_MOHAMMED_PFE_1.0.tex
echo -----------------------------------------

:: Exécution de pdflatex
xelatex -interaction=nonstopmode -file-line-error SBIHI_MOHAMMED_PFE_1.0.tex
:: Vérification si la compilation a réussi
if %errorlevel% equ 0 (
    echo -----------------------------------------
    echo [SUCCES] Le PDF a ete genere avec succes.

) else (
    echo -----------------------------------------
    echo [ERREUR] Un probleme est survenu durant la compilation.
)
    del SBIHI_MOHAMMED_PFE_1.0.aux
    del SBIHI_MOHAMMED_PFE_1.0.log
    del SBIHI_MOHAMMED_PFE_1.0.out
    del SBIHI_MOHAMMED_PFE_1.0.toc
    del SBIHI_MOHAMMED_PFE_1.0.lof
    del SBIHI_MOHAMMED_PFE_1.0.lot
    del SBIHI_MOHAMMED_PFE_1.0.fdb_latexmk
    del SBIHI_MOHAMMED_PFE_1.0.fls
    del SBIHI_MOHAMMED_PFE_1.0.xdv
pause