#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <map>

namespace py = pybind11;

// Funzione Quant: Calcola l'efficienza realizzativa pesata per la volatilità
// Più alto è lo score, più il giocatore è un "cecchino" affidabile
double calculate_efficiency(const std::vector<double>& xg, const std::vector<int>& goals) {
    if (xg.size() != goals.size() || xg.empty()) {
        return 0.0;
    }

    double total_xg = 0.0;
    double total_goals = 0.0;
    double variance_sum = 0.0;

    for (size_t i = 0; i < xg.size(); ++i) {
        total_xg += xg[i];
        total_goals += static_cast<double>(goals[i]);
        
        // Calcoliamo quanto la performance singola devia dall'aspettativa
        double diff = goals[i] - xg[i];
        variance_sum += diff * diff;
    }

    double raw_overperformance = total_goals - total_xg;
    double volatility = std::sqrt(variance_sum / xg.size());

    // Se la volatilità è 0 (impossibile), evitiamo divisione per zero
    if (volatility < 1e-6) volatility = 1.0;

    // FORMULA QUANT: Overperformance normalizzata dal rischio (simile allo Sharpe Ratio in finanza)
    return raw_overperformance / volatility;
}
// Aggiungi in alto
#include <numeric>

// ... (lascia la funzione calculate_efficiency vecchia) ...

// NUOVA FUNZIONE: Calcola il trend recente (Linear Regression Slope)
// Restituisce > 0 se il giocatore è in crescita, < 0 se è in calo
double calculate_trend(const std::vector<double>& values) {
    size_t n = values.size();
    if (n < 2) return 0.0;

    double sum_x = 0.0, sum_y = 0.0, sum_xy = 0.0, sum_xx = 0.0;
    
    for (size_t i = 0; i < n; ++i) {
        sum_x += i;
        sum_y += values[i];
        sum_xy += i * values[i];
        sum_xx += i * i;
    }

    double slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x);
    return slope;
}
// Funzione Helper: Calcola la magnitudine (lunghezza) di un vettore
double magnitude(const std::vector<double>& v) {
    double sum = 0.0;
    for (double val : v) sum += val * val;
    return std::sqrt(sum);
}

// NUOVA FUNZIONE: Trova i top N giocatori simili
// target_features: le stats del giocatore che cerchi (es. Vlahovic)
// database_features: le stats di TUTTI i giocatori
// Restituisce: Lista di indici (della matrice database) e score di somiglianza (0.0 a 1.0)
std::vector<std::pair<int, double>> find_similar_players(
    const std::vector<double>& target_features, 
    const std::vector<std::vector<double>>& database_features,
    int top_n = 5
) {
    std::vector<std::pair<int, double>> scores;
    double target_mag = magnitude(target_features);
    
    if (target_mag == 0) return scores; // Evita divisione per zero

    for (size_t i = 0; i < database_features.size(); ++i) {
        const auto& other = database_features[i];
        double other_mag = magnitude(other);
        
        if (other_mag == 0) continue;

        // Calcolo Dot Product
        double dot = 0.0;
        for (size_t k = 0; k < target_features.size(); ++k) {
            dot += target_features[k] * other[k];
        }

        // Cosine Similarity Formula: (A . B) / (||A|| * ||B||)
        double similarity = dot / (target_mag * other_mag);
        
        scores.push_back({(int)i, similarity});
    }

    // Ordina per somiglianza decrescente (dal più simile al meno simile)
    std::sort(scores.begin(), scores.end(), [](const std::pair<int, double>& a, const std::pair<int, double>& b) {
        return a.second > b.second;
    });

    // Taglia ai primi N risultati
    if (scores.size() > top_n) {
        scores.resize(top_n);
    }

    return scores;
}

// NUOVA FUNZIONE: Stima Fair Value (Performance-Based Market Value)
// Formula: Base Value + (Goals * 2M) + (xG * 1M) + (Assists * 1.2M) - Penalty per pochi minuti
// Restituisce: Valore stimato in MILIONI di Euro
double estimate_fair_value(int goals, int assists, double total_xg, int minutes) {
    // Base value: tutti i giocatori hanno un minimo
    double base_value = 1.0; // 1M €
    
    // Performance multipliers
    double goals_value = goals * 2.0;        // 2M per goal
    double xg_value = total_xg * 1.0;        // 1M per xG
    double assists_value = assists * 1.2;    // 1.2M per assist
    
    // Minutes penalty: se ha giocato poco, il valore è incerto (riduciamo)
    double minutes_multiplier = 1.0;
    if (minutes < 500) {
        minutes_multiplier = 0.5; // -50% se ha giocato meno di 500 minuti
    } else if (minutes < 1000) {
        minutes_multiplier = 0.75; // -25% se ha giocato meno di 1000 minuti
    }
    
    // Calcolo finale
    double raw_value = base_value + goals_value + xg_value + assists_value;
    double adjusted_value = raw_value * minutes_multiplier;
    
    // Cap: nessun giocatore vale più di 100M (realistico per Serie A)
    if (adjusted_value > 100.0) adjusted_value = 100.0;
    
    return adjusted_value;
}

// Qui "esponiamo" le funzioni a Python
PYBIND11_MODULE(quant_engine, m) {
    m.doc() = "Modulo C++ per calcoli statistici avanzati sul calcio";
    m.def("calculate_efficiency", &calculate_efficiency, "Calcola efficienza pesata su rischio");
    m.def("calculate_trend", &calculate_trend, "Calcola il trend recente delle performance tramite regressione lineare");
    m.def("find_similar_players", &find_similar_players, "Trova i top N giocatori simili basati su cosine similarity");
    m.def("estimate_fair_value", &estimate_fair_value, "Stima il Fair Value (valore di mercato) basato su performance");
}