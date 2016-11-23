

def run_golden_truth(plot=False):
    true_counts_file = os.path.join(results_folder, "true_counts.p")
    if os.path.isfile(true_counts_file):
        true_counts_d = pickle.load(open(true_counts_file, "rb"))
    else:
        decease_file = (settings.global_settings['csv_form_path']).replace('decease', decease)
        golden_folder = os.path.join(results_folder, "distributions_t")
        if not os.path.exists(golden_folder):
            os.makedirs(golden_folder)
        true_counts_d = analyze_golden_truth(decease_file, decease_dict, decease_ids, decease_names_dict, golden_folder,
                                             plot)
        pickle.dump(true_counts, open(true_counts_file, "wb"))
    return true_counts_d


def store_majority_scores(true_counts_d):

    mj_file = os.path.join(results_folder, 'majority_scores.json')
    true_counts_1of_k = {}
    true_counts_open_q = {}
    for field_ in decease_dict:
        if decease_dict[field_]['values'] == "unknown":
            true_counts_open_q[field_] = true_counts_d[field_]
        else:
            true_counts_1of_k[field_] = true_counts_d[field_]
    maj_dict_1ofk, maj_score_1ofk = get_majority_assignment_score(true_counts_1of_k, len(decease_ids))
    maj_dict_open_q, maj_score_open_q = get_majority_assignment_score(true_counts_open_q, len(decease_ids))
    maj_results = {'1_of_k': [maj_dict_1ofk, maj_score_1ofk], 'open_q': [maj_dict_open_q, maj_score_open_q]}
    with open(mj_file, 'w') as mf:
        data = json.dumps(maj_results, separators=[',', ':'], indent=4, sort_keys=True)
        mf.write(data)


def get_majority_assignment_score(counts_dict, num_assign_patients):
    # for one form
    # counts_dict format: {'field1':{'v1':x times, 'v2':y times..}'field2':{}...}
    # majority_score_dict format: {'field1': score, 'field2':score...}
    # where each score is found as counts of most occurring value / num of patients assigned

    # print "in get_majority_assignment_score counts_dict is:\n{}\nand num_assign_patients is: {}".\
    #     format(counts_dict, num_assign_patients)
    avg_score = 0.0
    majority_score_dict = {}
    for field in counts_dict.keys():
        counts = counts_dict[field].values()
        test = np.asarray(counts)
        assert np.sum(test) == num_assign_patients, "eep"
        max_idx, max_val = max(enumerate(counts), key=operator.itemgetter(1))
        majority_score_dict[field] = max_val/num_assign_patients
        avg_score += majority_score_dict[field]

    avg_score /= len(counts_dict.keys())
    print "in get_majority_assignment_score results {}\n{}".format(majority_score_dict, avg_score)
    return majority_score_dict, avg_score


def get_golden_truth_distribution(data_file, fields_dict, accepted_ids, names_dict):
    # receives the csv of the (golden truth) decease's values and returns a distribution of the counts
    # note: also receives the ids used in predictions
    # note: also receives a dictionary to replace values with shorter names

    fields_list = ['PatientNr']
    fields_data_types = {'PatientNr': str}
    with_counts_dict = {}

    for field in fields_dict:
        fields_list.append(str(field))
        fields_data_types[field] = str
        with_counts_dict[field] = {}

    num_accepted_patients = len(accepted_ids)
    df = pd.read_csv(data_file, usecols=fields_list, dtype=fields_data_types)
    # accepted_df = df[df['PatientNr'].isin(accepted_ids)]  # remove unused patients

    ids = accepted_ids[:]  # WOW  its send by reference !
    indices_to_del = []
    for index_, row in df.iterrows():
        if row['PatientNr'] in ids:
            idx = ids.index(row['PatientNr'])
            del ids[idx]
        else:
            indices_to_del.append(index_)
    accepted_df = df.drop(df.index[indices_to_del])
    # print "shape ", accepted_df.shape, " ", df.shape, " ", len(accepted_ids)

    for field in fields_list[1:]:
        possible_values = fields_dict[field]['values']
        field_total = 0
        if possible_values == "unknown":
            counts_field_nan = accepted_df[accepted_df[field].isnull()].shape[0]
            with_counts_dict[field]['NaN'] = counts_field_nan
            field_total += counts_field_nan
            with_counts_dict[field][possible_values] = num_accepted_patients - field_total
        else:
            for i, possible_value in enumerate(possible_values):
                counts_field_value = accepted_df[accepted_df[field] == possible_value].shape[0]
                if field in names_dict.keys():
                    with_counts_dict[field][names_dict[field][possible_value]] = counts_field_value
                else:
                    with_counts_dict[field][possible_value] = counts_field_value
                field_total += counts_field_value
                with_counts_dict[field]['NaN'] = num_accepted_patients - field_total
    print "in get_golden_truth_distribution results are:\n{}".format(with_counts_dict)
    return with_counts_dict


def analyze_golden_truth(data_file, fields_dict, accepted_ids, names_dict, out_folder, plot=False):
    decease_counts = get_golden_truth_distribution(data_file, fields_dict, accepted_ids, names_dict)
    if plot:
        plot_counts(decease_counts, out_folder)
    return decease_counts