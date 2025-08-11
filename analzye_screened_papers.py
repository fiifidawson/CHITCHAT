def calculate_phase_results(screening: PaperScreening) -> Dict[str, Any]:
    """Calculate phase pass/fail based on raw assessments."""
    
    # Phase 1 calculation
    pub_quality = screening.publication_quality
    tech_scope = screening.technical_scope
    
    phase1_pub_passed = (
        pub_quality.is_top_tier_venue and
        pub_quality.publication_year >= 2020 and
        (pub_quality.citation_count >= 10 or pub_quality.is_recent_promising) and
        pub_quality.full_text_english
    )
    
    phase1_tech_passed = (
        tech_scope.addresses_llm_data_collection or
        tech_scope.addresses_text_corpus_creation or
        tech_scope.addresses_web_scraping_nlp or
        tech_scope.addresses_multilingual_compilation
    )
    
    phase1_passed = phase1_pub_passed and phase1_tech_passed
    
    # Phase 2 calculation
    ethical = screening.ethical_flags
    humanitarian = screening.humanitarian_principles
    
    humanitarian_total = (
        humanitarian.humanity_score +
        humanitarian.impartiality_score +
        humanitarian.independence_score +
        humanitarian.neutrality_score
    )
    
    phase2_failed = (
        ethical.focuses_only_on_performance or
        ethical.disregards_ethical_principles or
        ethical.missing_ethical_approval or
        ethical.violates_humanitarian_principles or
        humanitarian_total < 6
    )
    
    phase2_passed = not phase2_failed
    
    # Phase 3 calculation
    methodology = screening.methodology_contributions
    ethics_contrib = screening.ethical_contributions
    
    has_methodology_value = (
        methodology.novel_methodology or
        methodology.systematic_evaluation or
        methodology.reproducible_implementation
    )
    
    has_ethical_value = (
        ethics_contrib.explicit_framework or
        ethics_contrib.empirical_bias_analysis or
        ethics_contrib.harm_mitigation_strategies or
        ethics_contrib.policy_recommendations or
        ethics_contrib.acknowledges_tensions
    )
    
    return {
        "phase1_passed": phase1_passed,
        "phase1_details": {
            "publication_quality_passed": phase1_pub_passed,
            "technical_scope_passed": phase1_tech_passed
        },
        "phase2_passed": phase2_passed,
        "phase2_details": {
            "humanitarian_total_score": humanitarian_total,
            "has_ethical_violations": phase2_failed
        },
        "phase3_details": {
            "has_methodology_contribution": has_methodology_value,
            "has_ethical_contribution": has_ethical_value
        }
    }