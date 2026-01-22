# LLM Model Comparison: qwen2.5:7b vs qwen3:8b

## Overview
Compared two Ollama models for automatic keyword extraction from academic papers.

## Test Setup
- **Task**: Extract research method (quantitative/qualitative/conceptual) + 5-6 keywords
- **Input**: Abstract text from 22 academic papers
- **Goal**: 100% automatic processing with no manual intervention

## Results

### qwen2.5:7b (Recommended)
- **Success Rate**: 22/22 (100%)
- **Processing**: Simple, direct responses
- **Output Format**: Consistent `method, keyword1, keyword2, ...`
- **Speed**: Fast (~3-5 seconds per paper)
- **Reliability**: Never returns empty or malformed responses

**Method Distribution:**
- Quantitative: 10 papers
- Qualitative: 6 papers
- Conceptual: 6 papers

### qwen3:8b (Not Recommended for This Task)
- **Success Rate**: ~15/22 (68%)
- **Processing**: Thinking mode adds complexity
- **Output Format**: Inconsistent - sometimes returns:
  - "method, keyword1, ..." (literal word "method")
  - Empty responses
  - "[conceptual], [keyword1], ..." (with brackets)
  - Proper format (when it works)
- **Speed**: Slower (~5-8 seconds per paper)
- **Reliability**: Frequently fails on certain papers (P001, P011, P019, P021)

**Issues Encountered:**
- Empty responses: 4 papers
- Placeholder text: 2 papers (literal "keyword1, keyword2, ...")
- Required complex parsing logic to handle multiple output formats
- Inconsistent method inference needed

## Key Findings

### Why qwen2.5:7b Works Better

1. **Simpler is Better**: Without thinking mode, the model outputs directly
2. **Consistent Format**: Always follows the requested format
3. **Reliable**: Never fails to produce output
4. **Easier to Parse**: Simple pattern matching works 100% of the time

### Why qwen3:8b Underperforms

1. **Thinking Mode Overhead**: The model's internal reasoning sometimes interferes with output
2. **Format Confusion**: Sometimes outputs literal "method" instead of actual method type
3. **Incomplete Responses**: Some papers trigger empty responses
4. **Requires Complex Parsing**: Need multiple fallback patterns to handle variations

## Sample Outputs

### Paper P008 (Quantitative RCT Paper)

**qwen2.5:7b:**
```
quantitative, entrepreneurial decision making, randomized control trial, scientific approach, startups, market feedback
```

**qwen3:8b:**
```
quantitative, entrepreneurial decision making, randomized control trial, startups, scientific approach, hypothesis testing
```
Both correct, slightly different keywords.

### Paper P013 (Conceptual Paper)

**qwen2.5:7b:**
```
qualitative, lean startup, theory-based view, scientific method, startups, rationality
```

**qwen3:8b:**
```
conceptual, scientific method, lean startup, theory-based view, generative rationality, bounded rationality
```
Different method classification - qwen3 more accurate (conceptual vs qualitative).

### Paper P001 (Quantitative Paper)

**qwen2.5:7b:**
```
quantitative, entrepreneurial exit, innovation, management science, exits, ventures
```

**qwen3:8b:**
```
(empty response)
```
qwen3 failed completely.

## Recommendation

**Use qwen2.5:7b** for production keyword extraction because:
- 100% success rate is critical for automatic processing
- Consistency matters more than occasional better keyword selection
- Simpler implementation = fewer edge cases = more maintainable

**qwen3:8b advantages don't outweigh reliability issues:**
- Slightly more detailed keywords (when it works) < 100% reliability
- Better model on paper ≠ better model for this specific task

## Technical Details

### Abstract Extraction
Both models use the same abstract extraction:
- First 2 pages of PDF
- Regex patterns to find "Abstract:" section
- Fallback to first 1500 chars if no abstract found

### Prompt (Identical for Both)
```
Classify this paper and extract keywords.

Method (choose ONE): quantitative (numbers/stats/data), qualitative (cases/interviews), mixed (both), conceptual (pure theory)

Title: {title}
Abstract: {abstract}

Output exactly in this format: method, keyword1, keyword2, keyword3, keyword4, keyword5

Answer:
```

### Parsing Logic

**qwen2.5:7b** (simple):
- Direct pattern match: `(quantitative|qualitative|...), keyword1, ...`
- Success rate: 100%

**qwen3:8b** (complex):
- Pattern 1: Check for `(quantitative|qualitative|...), keyword1, ...`
- Pattern 2: Handle `method, keyword1, ...` and infer actual method
- Pattern 3: Handle `[method], [keyword1], ...` format
- Pattern 4: Multiple fallbacks for edge cases
- Success rate: 68%

## Conclusion

For **automatic, production-ready keyword extraction**, **qwen2.5:7b is the clear winner** despite being a smaller model. The lesson: model size and sophistication don't guarantee better performance for specific tasks. Reliability and consistency are more valuable than occasional higher-quality outputs.
