#!/usr/bin/env python3
"""
Benchmark pentru algoritmi SAT pe fișiere .cnf

Scanează un fișier sau un director cu fișiere DIMACS-CNF și rulează următorii algoritmi:
  • Brute-Force (doar dacă variabilele <= BF_THRESHOLD)
  • Davis–Putnam (cu memoizare, limită de pași și timeout intern)
  • DPLL
  • CDCL (folosind python-sat)

Pentru fiecare algoritm măsoară:
  - rezultatul (SAT/UNSAT)
  - timpul de execuție
  - memoria maximă folosită

Cerințe:
    pip install psutil
    pip install python-sat[pblib,aiger]
"""

import os, sys, time, psutil, argparse, random
from multiprocessing import Process, Queue

# ---------------------------- Configurații ----------------------------
TIMEOUT_PER_SOLVER = 30        # timeout global per algoritm (secunde)
MAX_DP_STEPS      = 100_000    # limită internă pentru algoritmul DP
BF_THRESHOLD      = 20         # peste acest număr de variabile, Brute-Force este ignorat

# ---------------------------- Parser CNF ----------------------------
def parse_cnf_file(path):
    """
    Parsează un fișier DIMACS CNF.
    Ignoră liniile cu 'c', comentariile inline după '%' și liniile goale.
    Returnează: (formulă: listă de clauze), număr variabile, număr clauze.
    """
    formula = []
    n_vars = n_clauses = None
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('c'):
                continue
            if line.startswith('%'):
                break
            if line.startswith('p cnf'):
                parts = line.split()
                n_vars, n_clauses = int(parts[2]), int(parts[3])
                continue
            if '%' in line:
                line = line.split('%', 1)[0].strip()
                if not line:
                    continue
            lits = []
            for tok in line.split():
                v = int(tok)
                if v == 0:
                    break
                lits.append(v)
            if lits:
                formula.append(lits)
    if n_vars is None or n_clauses is None:
        raise ValueError(f"Header 'p cnf' lipsă în {path}")
    return formula, n_vars, n_clauses

# ---------------------------- Algoritmi SAT ----------------------------
def brute_force_solver(formula):
    """Caută toate cele 2^n combinații posibile de valori (True/False)"""
    n = max(abs(l) for c in formula for l in c)
    for mask in range(1 << n):
        if all(
            any((lit > 0) == bool((mask >> (abs(lit)-1)) & 1) for lit in clause)
            for clause in formula
        ):
            return True
    return False

def dp_solver(formula):
    """
    Algoritmul Davis–Putnam cu memoizare, limită de pași și timeout.
    Aruncă TimeoutError dacă se depășesc limitele.
    """
    start = time.time()
    def resolve(fm, seen, steps):
        if time.time() - start > TIMEOUT_PER_SOLVER:
            raise TimeoutError("Timp depășit pentru DP")
        steps[0] += 1
        if steps[0] > MAX_DP_STEPS:
            raise TimeoutError("Limită de pași depășită pentru DP")
        sig = frozenset(frozenset(c) for c in fm)
        if sig in seen:
            return False
        seen.add(sig)
        if not fm:
            return True
        if any(len(c) == 0 for c in fm):
            return False
        x = abs(fm[0][0])
        pos = [c for c in fm if x in c]
        neg = [c for c in fm if -x in c]
        rest = [c for c in fm if x not in c and -x not in c]
        new = []
        for p in pos:
            for q in neg:
                rc = [l for l in p if abs(l)!=x] + [l for l in q if abs(l)!=x]
                S = set(rc)
                if any(-lit in S for lit in S):
                    continue
                new.append(list(dict.fromkeys(rc)))
        return resolve(rest + new, seen, steps)
    return resolve(formula, seen=set(), steps=[0])

def dpll_solver(formula):
    """DPLL cu propagare unitară și eliminarea literalilor puri"""
    def simplify(frm, lit):
        out = []
        for c in frm:
            if lit in c:
                continue
            if -lit in c:
                c = [l for l in c if l != -lit]
            out.append(c)
        return out
    while True:
        units = [c[0] for c in formula if len(c) == 1]
        if not units:
            break
        for u in units:
            formula = simplify(formula, u)
    lits = [l for c in formula for l in c]
    pures = [v for v in set(abs(l) for l in lits) if (v in lits) ^ (-v in lits)]
    for v in pures:
        lit = v if v in lits else -v
        formula = simplify(formula, lit)
    if not formula:
        return True
    if any(len(c) == 0 for c in formula):
        return False
    lit = formula[0][0]
    return (dpll_solver(simplify(formula, lit)) or
            dpll_solver(simplify(formula, -lit)))

def cdcl_solver(formula):
    """CDCL folosind biblioteca python-sat (solver Glucose3)"""
    try:
        from pysat.solvers import Solver
    except ImportError:
        print("ERROR: Instalează python-sat[pblib,aiger]", file=sys.stderr)
        sys.exit(1)
    with Solver(name='glucose3') as s:
        for clause in formula:
            s.add_clause(clause)
        return s.solve()

# ---------------------------- Executor cu timeout ----------------------------
def _worker(func, formula, q):
    try:
        start = time.time()
        res = func(formula)
        elapsed = time.time() - start
        mem_mb = psutil.Process(os.getpid()).memory_info().rss / (1024**2)
        q.put({'result': res, 'time': elapsed, 'memory': mem_mb})
    except TimeoutError:
        q.put({'timeout': True})
    except Exception:
        q.put({'timeout': True})

def run_with_timeout(func, formula):
    q = Queue()
    p = Process(target=_worker, args=(func, formula, q))
    p.start()
    p.join(TIMEOUT_PER_SOLVER)
    if p.is_alive():
        p.terminate()
        p.join()
        return {'timeout': True}
    info = q.get() if not q.empty() else {'timeout': True}
    return info

# ---------------------------- Main (executare) ----------------------------
def main():
    parser = argparse.ArgumentParser(description="Benchmark algoritmi SAT pe fișiere .cnf")
    parser.add_argument('path', help="Fișier .cnf sau director cu fișiere .cnf")
    args = parser.parse_args()

    if os.path.isdir(args.path):
        files = sorted(os.path.join(args.path, f)
                       for f in os.listdir(args.path)
                       if f.lower().endswith('.cnf'))
    elif args.path.lower().endswith('.cnf'):
        files = [args.path]
    else:
        print("Nu am găsit fișiere .cnf la", args.path, file=sys.stderr)
        sys.exit(1)

    solvers = [
        ("Brute-Force", brute_force_solver),
        ("Davis–Putnam", dp_solver),
        ("DPLL",         dpll_solver),
        ("CDCL",         cdcl_solver),
    ]

    for path in files:
        print(f"\n=== {os.path.basename(path)} ===")
        try:
            formula, n, m = parse_cnf_file(path)
            print(f"Variabile: {n}, Clauze: {m}")
        except Exception as e:
            print(f"Eroare la parsare: {e}", file=sys.stderr)
            continue

        for name, solver in solvers:
            if name == "Brute-Force" and n > BF_THRESHOLD:
                print(f"-- {name:12} SĂRIT (n>{BF_THRESHOLD})")
                continue
            print(f"-- {name:12} ", end='', flush=True)
            info = run_with_timeout(solver, formula)
            if info.get('timeout'):
                print("TIMEOUT")
            else:
                sat = info['result']
                print(f"{'SAT' if sat else 'UNSAT'}, "
                      f"{info['time']:.2f}s, {info['memory']:.1f}MB")

    print("\n=== Benchmark finalizat ===")

if __name__ == "__main__":
    main()