from __future__ import print_function, division
import numpy as np
from treetime import TreeTime
from Bio import Phylo, AlignIO

if __name__=="__main__":
    ###########################################################################
    ### parameter parsing
    ###########################################################################
    import argparse
    parser = argparse.ArgumentParser(
            description="Reconstruct ancestral sequences, set dates to tree, and infer a time scaled tree."
                        " The ancestral sequences will be written to a file ending on _ancestral.fasta"
                        " A tree in newick format with mutations as _A45G_... appended"
                        " appended to node names will be written to a file ending on _mutation.newick")
    parser.add_argument('--aln', required = True, type = str,  help ="fasta file with input sequences")
    parser.add_argument('--tree', required = True, type = str,  help ="newick file with tree")
    parser.add_argument('--dates', required = True, type = str,
                        help ="csv with dates for nodes with 'node_name, date' where date is float (as in 2012.15)")
    parser.add_argument('--infer_gtr', default = True, action='store_true', help='infer substitution model')
    parser.add_argument('--reroot', required = False, type = str, default='best',
                        help ="reroot the tree. Valid arguments are 'best', 'midpoint', or a node name")
    parser.add_argument('--resolve_polytomies', default = True, action='store_true',
                        help='resolve polytomies using temporal information')
    parser.add_argument('--relax',nargs='*', default = False,
                        help='autocorrelated molecular clock with prior strength and coupling of parent and offspring rates')
    parser.add_argument('--max_iter', default = 2, type=int,
                        help='maximal number of iterations the inference cycle is run')
    parser.add_argument('--verbose', default = 3, type=int,
                        help='verbosity of output 0-6')
    parser.add_argument('--Tc', default = 0.0, type=float,
                        help='coalescent time scale -- sensible values are on the order of the average '
                             'hamming distance of contemporaneous sequences')
    parser.add_argument('--plot', default = False, action='store_true',
                        help='plot the tree with a time axis')
    params = parser.parse_args()
    if params.relax==[]:
        params.relax=True
    if params.Tc<1e-5: params.Tc=False

    ###########################################################################
    ### PARSING DATES
    ###########################################################################
    with open(params.dates) as date_file:
        dates = {}
        for line in date_file:
            try:
                name, date = line.strip().split(',')[:2]
                dates[name] = float(date)
            except:
                continue

    ###########################################################################
    ### ANCESTRAL RECONSTRUCTION AND SET-UP
    ###########################################################################
    myTree = TreeTime(dates=dates, tree=params.tree,
                       aln=params.aln, gtr='JC69', verbose=params.verbose)
    myTree.run(root=params.reroot, relaxed_clock=params.relax,
               resolve_polytomies=params.resolve_polytomies,
               Tc=params.Tc, max_iter=params.max_iter)

    ###########################################################################
    ### OUTPUT and saving of results
    ###########################################################################
    if params.infer_gtr:
        print('\nInferred GTR model:')
        print(myTree.gtr)

    print(myTree.date2dist)
    base_name = '.'.join(params.aln.split('/')[-1].split('.')[:-1])

    # plot
    if params.plot:
        from treetime.io import plot_vs_years
        import matplotlib.pyplot as plt
        leaf_count = myTree.tree.count_terminals()
        label_func = lambda x: x.name[:20] if leaf_count<30 else ''
        branch_label_func = lambda x: (','.join([a+str(pos)+d for a,pos, d in x.mutations[:10]])
                                       +('...' if  len(x.mutations)>10 else '')) if leaf_count<30 else ''
        plot_vs_years(myTree, show_confidence=False, label_func = label_func, branch_labels=branch_label_func)
        plt.savefig(base_name+'_tree.pdf')


    # decorate tree with inferred mutations
    outaln_name = base_name+'_ancestral.fasta'
    AlignIO.write(myTree.get_reconstructed_alignment(), outaln_name, 'fasta')
    for n in myTree.tree.find_clades():
        if n.up is None:
            continue
        if len(n.mutations):
            n.name+='_'+'_'.join([a+str(pos)+d for (a,pos, d) in n.mutations])

    # write tree to file. Branch length will now be scaled such that node
    # positions correspond to sampling times.
    outtree_name = base_name+'_timetree.newick'
    Phylo.write(myTree.tree, outtree_name, 'newick')
