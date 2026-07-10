"""
Engine 1.5 — Dataset Lineage Engine
Builds a source-to-target lineage graph from the parsed AST.
Runs after the Parser Engine and before the Intent Engine.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional

from .parser_engine import ParseResult


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LineageNode:
    name: str
    node_type: str          # 'source' | 'intermediate' | 'output' | 'external'
    library: str = 'work'
    full_name: str = ''     # libref.name
    created_by: str = ''    # 'data_step' | 'proc_sort' | 'proc_import' etc.
    operations: List[str] = field(default_factory=list)

@dataclass
class LineageEdge:
    source: str
    target: str
    operation: str          # 'set' | 'merge' | 'sort' | 'transpose' | 'import' | ...
    join_type: str = ''     # 'left_join' | 'inner_join' | 'full_join' | ''
    by_vars: List[str] = field(default_factory=list)

@dataclass
class LineageResult:
    nodes: Dict[str, LineageNode]
    edges: List[LineageEdge]
    lineage_map: Dict[str, List[str]]   # dataset_name → [parent dataset names]
    summary: str
    mermaid: str


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class LineageEngine:
    """
    Parses the AST to build a directed acyclic graph of dataset dependencies.
    """

    def build(self, pr: ParseResult) -> LineageResult:
        nodes: Dict[str, LineageNode] = {}
        edges: List[LineageEdge] = []
        lineage_map: Dict[str, List[str]] = {}

        # Context tracking across AST nodes
        current_ds: Optional[str] = None
        current_lib: str = 'work'
        pending_sets: List[str] = []
        pending_merge_ds: List[Dict] = []
        by_vars: List[str] = []

        def _add_node(name: str, lib: str = 'work', full: str = '',
                      node_type: str = 'intermediate', created_by: str = '') -> None:
            if name not in nodes:
                nodes[name] = LineageNode(
                    name=name, node_type=node_type, library=lib,
                    full_name=full or f"{lib}.{name}" if lib != 'work' else name,
                    created_by=created_by,
                )

        # Track datasets created by prior data steps for accurate source/target labeling
        script_created: Set[str] = set()
        pending_join_type: str = 'left_join'

        for node in pr.ast:
            t = node.get('type', '')

            if t == 'libname':
                pass  # purely declarative — no lineage edge

            elif t == 'data_step':
                current_ds  = node.get('dataset', '')
                current_lib = node.get('library', 'work')
                pending_sets = []
                pending_merge_ds = []
                by_vars = []
                pending_join_type = 'left_join'
                if current_ds:
                    _add_node(current_ds, current_lib, created_by='data_step')

            elif t == 'set':
                ds_list  = node.get('datasets', [])
                full_list = node.get('full_datasets', ds_list)
                for ds_name, full_name in zip(ds_list, full_list):
                    lib_part = 'work'
                    if '.' in str(full_name):
                        lib_part = str(full_name).split('.', 1)[0]
                    # Use 'intermediate' if already created in this script, else 'source'
                    ntype = 'intermediate' if ds_name in script_created else 'source'
                    _add_node(ds_name, lib_part, str(full_name), node_type=ntype,
                              created_by='set')
                    pending_sets.append(ds_name)

            elif t == 'merge':
                pending_merge_ds = node.get('datasets', [])
                for d in pending_merge_ds:
                    ds_name  = d.get('name', '')
                    full_name = d.get('full_name', ds_name)
                    lib_part  = d.get('libref', 'work')
                    if ds_name:
                        ntype = 'intermediate' if ds_name in script_created else 'source'
                        _add_node(ds_name, lib_part, full_name, node_type=ntype,
                                  created_by='merge')

            elif t == 'if_statement':
                # Infer join type from "if a;" / "if a and b;" / "if not b;" merge conditions
                cond = (node.get('condition') or '').strip().lower()
                if pending_merge_ds and node.get('then_clause') is None:
                    in_vars = {d.get('in_var', '').lower() for d in pending_merge_ds
                               if d.get('in_var')}
                    if cond in in_vars:
                        pending_join_type = 'left_join'
                    elif re.match(r'^(\w+)\s+(?:and|&)\s+(\w+)$', cond):
                        pending_join_type = 'inner_join'
                    elif re.match(r'^not\s+(\w+)$', cond) and cond.split()[-1] in in_vars:
                        pending_join_type = 'anti_join'

            elif t == 'by':
                by_vars = node.get('variables', [])

            elif t == 'run':
                if current_ds:
                    _add_node(current_ds, current_lib, created_by='data_step')
                    lineage_map.setdefault(current_ds, [])

                    if pending_sets:
                        if len(pending_sets) > 1:
                            for src in pending_sets:
                                edges.append(LineageEdge(src, current_ds, 'bind_rows'))
                                lineage_map[current_ds].append(src)
                        else:
                            src = pending_sets[0]
                            if src != current_ds:
                                edges.append(LineageEdge(src, current_ds, 'set'))
                                lineage_map[current_ds].append(src)
                        pending_sets = []

                    if pending_merge_ds and len(pending_merge_ds) >= 2:
                        left  = pending_merge_ds[0]['name']
                        right = pending_merge_ds[1]['name']
                        keep_left  = pending_merge_ds[0].get('keep', [])
                        keep_right = pending_merge_ds[1].get('keep', [])
                        edges.append(LineageEdge(
                            left, current_ds, 'merge',
                            join_type=pending_join_type,
                            by_vars=list(by_vars),
                        ))
                        edges.append(LineageEdge(
                            right, current_ds, 'merge',
                            join_type=pending_join_type,
                            by_vars=list(by_vars),
                        ))
                        lineage_map[current_ds] += [left, right]
                        pending_merge_ds = []

                    # Mark this dataset as created so downstream steps see it as intermediate
                    script_created.add(current_ds)

            elif t in ('proc_sort', 'proc_freq', 'proc_means', 'proc_print',
                       'proc_logistic', 'proc_mixed', 'proc_phreg', 'proc_lifetest',
                       'proc_report', 'proc_tabulate', 'proc_compare', 'proc_contents',
                       'proc_univariate', 'proc_corr', 'proc_reg', 'proc_glm'):
                src_ds = node.get('options', {}).get('data', '')
                if src_ds:
                    _add_node(src_ds, node_type='intermediate', created_by=t)
                if t == 'proc_sort' and src_ds:
                    # sort is in-place — same dataset in and out
                    nodes[src_ds].operations.append('sort')
                elif src_ds:
                    nodes[src_ds].operations.append(t.replace('proc_', ''))

            elif t == 'proc_transpose':
                opts   = node.get('options', {})
                src_ds = opts.get('data', '')
                out_ds = opts.get('out', src_ds + '_t' if src_ds else '')
                if src_ds:
                    _add_node(src_ds, node_type='intermediate', created_by='proc_transpose')
                if out_ds:
                    _add_node(out_ds, node_type='output', created_by='proc_transpose')
                    edges.append(LineageEdge(src_ds, out_ds, 'transpose'))
                    lineage_map.setdefault(out_ds, [src_ds])

            elif t == 'proc_import':
                opts    = node.get('options', {})
                out_ds  = opts.get('data', '')
                datafile = opts.get('datafile', '')
                if out_ds:
                    _add_node(out_ds, node_type='output', created_by='proc_import')
                    edges.append(LineageEdge(datafile or 'external_file', out_ds, 'import'))
                    lineage_map.setdefault(out_ds, [datafile or 'external_file'])

            elif t == 'proc_export':
                opts   = node.get('options', {})
                src_ds = opts.get('data', '')
                outfile = opts.get('outfile', 'output')
                if src_ds:
                    edges.append(LineageEdge(src_ds, outfile, 'export'))

        # Mark terminal nodes (nodes with no outgoing data-step edges) as 'output'
        sources: Set[str] = {e.source for e in edges}
        targets: Set[str] = {e.target for e in edges}
        for nm, nd in nodes.items():
            if nm in targets and nm not in sources and nd.node_type == 'intermediate':
                nd.node_type = 'output'
            elif nm not in targets and nd.node_type == 'intermediate':
                nd.node_type = 'source'

        summary = self._build_summary(nodes, edges)
        mermaid  = self._build_mermaid(nodes, edges)

        return LineageResult(
            nodes=nodes,
            edges=edges,
            lineage_map=lineage_map,
            summary=summary,
            mermaid=mermaid,
        )

    # ── helpers ──────────────────────────────────────────────────────────────

    def _build_summary(self, nodes: Dict[str, LineageNode],
                       edges: List[LineageEdge]) -> str:
        sources       = [n for n in nodes.values() if n.node_type == 'source']
        intermediates = [n for n in nodes.values() if n.node_type == 'intermediate']
        outputs       = [n for n in nodes.values() if n.node_type == 'output']
        parts = []
        if sources:
            parts.append(f"Source datasets: {', '.join(n.name.upper() for n in sources)}")
        if intermediates:
            parts.append(f"Intermediate: {', '.join(n.name.upper() for n in intermediates)}")
        if outputs:
            parts.append(f"Output datasets: {', '.join(n.name.upper() for n in outputs)}")
        if edges:
            ops = list({e.operation for e in edges})
            parts.append(f"Operations: {', '.join(ops)}")
        return " | ".join(parts) if parts else "No dataset lineage detected."

    def _build_mermaid(self, nodes: Dict[str, LineageNode],
                       edges: List[LineageEdge]) -> str:
        lines = ["graph LR"]
        for nm, nd in nodes.items():
            shape = f'["{nm.upper()}"]' if nd.node_type == 'source' else \
                    f'(("{nm.upper()}"))' if nd.node_type == 'output' else \
                    f'("{nm.upper()}")'
            lines.append(f"  {nm.replace('.', '_')}{shape}")
        for edge in edges:
            src = edge.source.replace('.', '_')
            tgt = edge.target.replace('.', '_')
            label = edge.join_type or edge.operation
            lines.append(f"  {src} -->|{label}| {tgt}")
        return "\n".join(lines)
