# 3-SAT-Benchmark
Acest program evaluează patru algoritmi de rezolvare SAT pe fișiere în format DIMACS 3-SAT:
- Brute-Force
- Davis–Putnam (DP)
- DPLL
- CDCL (folosind python-sat)

CERINȚE
-------
Înainte de rulare, instalează următoarele pachete în Python:

    pip install psutil
    pip install python-sat[pblib,aiger]

FIȘIERE ACCEPTATE
-----------------
Programul funcționează doar cu fișiere .cnf în format DIMACS.
Acestea trebuie să fie benchmarkuri 3-SAT (fiecare clauză are exact 3 litere).

Fișierele de test pot fi descărcate de la:
https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html

Asigură-te că fișierele .cnf sunt extrase într-un folder numit exact:
    cnf_files

INSTRUCȚIUNI DE RULARE
-----------------------
1. Navighează în folderul care conține fișierul Tester.py (click-dreapta pe fundalul folderului)
2. Alege opțiunea:
       Open Command Prompt here
   sau, dacă folosești PowerShell:
       Open in Terminal

3. Rulează comanda:
       python Tester.py cnf_files

Programul va parcurge automat toate fișierele .cnf din folderul `cnf_files` și va afișa:
- dacă formula este SAT/UNSAT/TIMEOUT
- timpul de execuție
- memoria fizică maximă utilizată (în MB)

EXEMPLU DE OUTPUT:
------------------
=== uf50-01.cnf ===
Vars: 50, Clauses: 218
-- Brute-Force   SKIPPED (n>20)
-- Davis–Putnam  TIMEOUT
-- DPLL          SAT, 0.12s, 9.3MB
-- CDCL          SAT, 0.03s, 11.5MB
