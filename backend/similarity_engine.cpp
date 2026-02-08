#include <vector>
#include <cmath>
#include <algorithm>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

// Struttura leggera per il risultato
struct MatchResult {
    int index;      // Indice nella lista originale (così Python risale al nome)
    double score;   // La distanza (più bassa è meglio)
};

// Funzione Core: Weighted Euclidean Distance
// Ottimizzata per velocità (loop unrolling automatico dal compilatore con -O3)
std::vector<MatchResult> find_similar_players(
    const std::vector<double>& target_features,
    const std::vector<std::vector<double>>& database,
    const std::vector<double>& weights,
    int top_n
) {
    std::vector<MatchResult> results;
    results.reserve(database.size()); // Pre-alloca memoria per efficienza

    // 1. Calcolo Distanze
    for (size_t i = 0; i < database.size(); ++i) {
        double sum_sq_diff = 0.0;
        
        // Calcolo distanza pesata dimensione per dimensione
        for (size_t j = 0; j < target_features.size(); ++j) {
            double diff = target_features[j] - database[i][j];
            sum_sq_diff += weights[j] * (diff * diff);
        }
        
        // Non serve fare sqrt per l'ordinamento (risparmiamo cicli CPU), 
        // ma la facciamo per restituire un valore leggibile all'utente.
        results.push_back({static_cast<int>(i), std::sqrt(sum_sq_diff)});
    }

    // 2. Ordinamento Parziale (nth_element è più veloce di sort completo se vuoi solo i top N)
    // Ma per N piccolo e dataset piccolo, sort va benissimo ed è stabile.
    std::sort(results.begin(), results.end(), [](const MatchResult& a, const MatchResult& b) {
        return a.score < b.score; // Ordine crescente (0 = identico)
    });

    // 3. Taglio ai Top N (+1 perché il primo è se stesso con distanza 0)
    if (results.size() > static_cast<size_t>(top_n + 1)) {
        results.resize(top_n + 1);
    }

    return results;
}

// Binding Pybind11: Espone la funzione a Python
PYBIND11_MODULE(similarity_engine, m) {
    m.doc() = "Motore di Scouting C++ per Football Quant Engine";
    
    py::class_<MatchResult>(m, "MatchResult")
        .def_readonly("index", &MatchResult::index)
        .def_readonly("score", &MatchResult::score);

    m.def("find_similar", &find_similar_players, "Trova i giocatori più simili dato un vettore di feature");
}