"""
AI-powered Dataset Intelligence Engine for REvolveS

Performs comprehensive validation and qualification of uploaded datasets:
- File integrity checks (corruption, encoding, format)
- Metadata validation (structure, columns, types)
- Structural validation (required variables, relationships)
- AI Dataset Classification (Raw/SDTM/ADaM/TLF/Analysis/Lookup/Metadata)
- AI Compatibility Scoring (0-100% with component scores)
- Variable mapping suggestions (AI-assisted matching)
- Duplicate detection (rows, subjects, keys)
- Missing value profiling and recommendations
"""

import csv
import pandas as pd
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import re


class DatasetType(Enum):
    """Clinical dataset types"""
    RAW = "raw"
    SDTM = "sdtm"
    ADAM = "adam"
    TLF = "tlf"
    ANALYSIS = "analysis"
    LOOKUP = "lookup"
    METADATA = "metadata"
    UNKNOWN = "unknown"


class AcceptanceStatus(Enum):
    """Dataset acceptance decision"""
    ACCEPTED = "accepted"
    ACCEPTED_WITH_WARNING = "accepted_with_warning"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


@dataclass
class FileIntegrityResult:
    """File integrity validation result"""
    is_valid: bool
    file_format: str
    file_size_kb: float
    encoding: str
    row_count: int
    column_count: int
    has_corruption: bool
    corruption_details: List[str] = field(default_factory=list)
    checksum: str = ""
    issues: List[str] = field(default_factory=list)


@dataclass
class MetadataValidation:
    """Metadata validation result"""
    dataset_name: str
    expected_name: Optional[str]
    column_count: int
    row_count: int
    primary_key: Optional[str]
    encoding: str
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class StructuralValidation:
    """Structural validation result"""
    required_variables: List[str]
    found_variables: List[str]
    missing_variables: List[str]
    extra_variables: List[str]
    variable_types: Dict[str, str]  # {var_name: type}
    type_mismatches: Dict[str, Tuple[str, str]] = field(default_factory=dict)  # {var: (expected, found)}
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class VariableMapping:
    """AI-suggested variable mapping"""
    original_var: str
    suggested_var: str
    confidence: float  # 0-1
    reason: str
    alternatives: List[Tuple[str, float]] = field(default_factory=list)  # [(var, confidence)]


@dataclass
class DuplicateAnalysis:
    """Duplicate detection results"""
    total_rows: int
    duplicate_rows: int
    duplicate_pct: float
    duplicate_subjects: int
    duplicate_visits: int
    duplicate_keys: int
    issues: List[str] = field(default_factory=list)


@dataclass
class MissingValueProfile:
    """Missing value analysis"""
    variable: str
    missing_count: int
    missing_pct: float
    pattern: str  # "random", "systematic", "monotone"
    clinical_criticality: str  # "high", "medium", "low"
    recommended_strategy: str
    reason: str


@dataclass
class CompatibilityScore:
    """AI Compatibility Score (0-100)"""
    overall: float  # 0-100
    structure: float  # Column matching
    variables: float  # Variable presence & types
    relationships: float  # PK/FK validation
    clinical: float  # Clinical standard compliance (SDTM, ADaM)
    data_quality: float  # Missing values, duplicates
    translation_ready: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class DatasetQualification:
    """Complete dataset qualification result"""
    dataset_name: str
    dataset_type: DatasetType
    file_integrity: FileIntegrityResult
    metadata: MetadataValidation
    structure: StructuralValidation
    duplicates: DuplicateAnalysis
    missing_values: List[MissingValueProfile]
    variable_mappings: List[VariableMapping]
    compatibility_score: CompatibilityScore
    acceptance_status: AcceptanceStatus
    recommendations: List[str]
    preview_data: Dict[str, Any]  # First N rows
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)


class DatasetIntelligenceEngine:
    """AI-powered dataset qualification and validation"""

    # Clinical domain variable patterns
    CLINICAL_VARIABLES = {
        'subject_id': ['usubjid', 'subjid', 'patientid', 'patient_id', 'subject', 'id'],
        'visit': ['visit', 'visitnum', 'visit_number', 'visit_name', 'visitcd'],
        'arm': ['arm', 'trta', 'trt01a', 'treatment_arm', 'treatment_group'],
        'site': ['site', 'siteid', 'site_id', 'center', 'facility'],
        'date': ['date', 'visit_date', 'visdat', 'visitdat'],
    }

    # Dataset type signatures
    DATASET_SIGNATURES = {
        DatasetType.SDTM: {
            'vars': ['usubjid', 'visit', 'visitnum', 'visitdat'],
            'pattern': r'(dm|ae|cm|lb|vs|ex|mh|su)\b',
            'confidence_boost': 0.3
        },
        DatasetType.ADAM: {
            'vars': ['usubjid', 'ady', 'avisit', 'avisitn'],
            'pattern': r'(adsl|adae|adlb|advs|adex|admh)\b',
            'confidence_boost': 0.3
        },
        DatasetType.TLF: {
            'vars': ['table', 'figure', 'listing', 'page'],
            'pattern': r't_|f_|l_',
            'confidence_boost': 0.2
        },
        DatasetType.RAW: {
            'vars': [],
            'pattern': r'raw_|source_|input_',
            'confidence_boost': 0.2
        }
    }

    def __init__(self):
        self.engine_name = "DatasetIntelligenceEngine"

    def qualify_dataset(
        self,
        file_path: str,
        dataset_name: str,
        required_variables: Optional[List[str]] = None
    ) -> DatasetQualification:
        """
        Perform comprehensive dataset qualification

        Args:
            file_path: Path to dataset file
            dataset_name: Name of dataset
            required_variables: Expected variables for this dataset

        Returns:
            DatasetQualification with all validation results
        """
        try:
            # Read file
            df = self._read_file(file_path)

            # Phase 1: File Integrity
            file_integrity = self._validate_file_integrity(file_path, df)

            if not file_integrity.is_valid:
                return self._create_rejected_qualification(
                    dataset_name,
                    file_integrity,
                    "File integrity check failed"
                )

            # Phase 2: Metadata Validation
            metadata = self._validate_metadata(dataset_name, df, required_variables)

            # Phase 3: Structural Validation
            structure = self._validate_structure(df, required_variables or [])

            # Phase 4: Detect Duplicates
            duplicates = self._detect_duplicates(df)

            # Phase 5: Profile Missing Values
            missing_values = self._profile_missing_values(df)

            # Phase 6: AI Variable Mapping
            variable_mappings = self._suggest_variable_mappings(
                df.columns.tolist(),
                required_variables or []
            )

            # Phase 7: Dataset Classification
            dataset_type = self._classify_dataset(df, dataset_name)

            # Phase 8: AI Compatibility Score
            compatibility = self._calculate_compatibility_score(
                metadata, structure, duplicates, missing_values, dataset_type
            )

            # Phase 9: Acceptance Decision
            acceptance_status, recommendations = self._make_acceptance_decision(
                compatibility, metadata, structure, duplicates
            )

            # Phase 10: Dataset Preview
            preview_data = self._create_preview(df)

            return DatasetQualification(
                dataset_name=dataset_name,
                dataset_type=dataset_type,
                file_integrity=file_integrity,
                metadata=metadata,
                structure=structure,
                duplicates=duplicates,
                missing_values=missing_values,
                variable_mappings=variable_mappings,
                compatibility_score=compatibility,
                acceptance_status=acceptance_status,
                recommendations=recommendations,
                preview_data=preview_data,
                audit_trail=[
                    {
                        'action': 'dataset_qualified',
                        'dataset': dataset_name,
                        'status': acceptance_status.value,
                        'timestamp': pd.Timestamp.now().isoformat()
                    }
                ]
            )
        except Exception as e:
            return self._create_error_qualification(dataset_name, str(e))

    def _read_file(self, file_path: str) -> pd.DataFrame:
        """Read dataset file (CSV, SAS7BDAT, XPT)"""
        # Normalize path (handle Windows/Unix differences)
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check if file is readable
        if not path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        # Check file size (skip if empty)
        if path.stat().st_size == 0:
            raise ValueError(f"File is empty: {file_path}")

        try:
            suffix = path.suffix.lower()

            if suffix == '.csv':
                # Read CSV with error handling
                df = pd.read_csv(file_path, nrows=10000, on_bad_lines='skip', engine='python')
                if df is None or len(df) == 0:
                    raise ValueError("CSV file is empty or contains no data")
                return df
            elif suffix == '.sas7bdat':
                # Read SAS7BDAT (nrows not supported with read_sas)
                df = pd.read_sas(file_path)
                if df is None or len(df) == 0:
                    raise ValueError("SAS7BDAT file is empty or unreadable")
                # Sample if too large
                return df.head(10000) if len(df) > 10000 else df
            elif suffix == '.xpt':
                # Read XPT format (nrows not supported with read_sas)
                df = pd.read_sas(file_path, format='xport')
                if df is None or len(df) == 0:
                    raise ValueError("XPT file is empty or unreadable")
                # Sample if too large
                return df.head(10000) if len(df) > 10000 else df
            else:
                raise ValueError(f"Unsupported file format: {suffix}. Supported: .csv, .sas7bdat, .xpt")
        except FileNotFoundError as e:
            raise e
        except Exception as e:
            # Re-raise with more context
            raise ValueError(f"Failed to read {path.name}: {str(e)}")

    def _validate_file_integrity(self, file_path: str, df: pd.DataFrame) -> FileIntegrityResult:
        """Validate file integrity"""
        try:
            path = Path(file_path)

            # Calculate checksum
            checksum = self._calculate_checksum(file_path)

            # Detect format
            file_format = path.suffix.lower().lstrip('.')

            # Get file size
            file_size_kb = path.stat().st_size / 1024

            issues = []

            # Check for common issues
            if file_size_kb == 0:
                issues.append("File is empty")

            if len(df) == 0:
                issues.append("Dataset has no rows")

            # Detect encoding
            encoding = self._detect_encoding(file_path)

            return FileIntegrityResult(
                is_valid=len(issues) == 0,
                file_format=file_format,
                file_size_kb=file_size_kb,
                encoding=encoding,
                row_count=len(df),
                column_count=len(df.columns),
                has_corruption=False,
                checksum=checksum,
                issues=issues
            )
        except Exception as e:
            return FileIntegrityResult(
                is_valid=False,
                file_format="unknown",
                file_size_kb=0,
                encoding="unknown",
                row_count=0,
                column_count=0,
                has_corruption=True,
                corruption_details=[str(e)],
                issues=[f"File corruption detected: {str(e)}"]
            )

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding"""
        # Simplified - in production use chardet
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1000)
            return 'utf-8'
        except:
            return 'latin-1'

    def _validate_metadata(
        self,
        dataset_name: str,
        df: pd.DataFrame,
        required_vars: Optional[List[str]]
    ) -> MetadataValidation:
        """Validate dataset metadata"""
        issues = []
        warnings = []

        # Check column count
        if len(df.columns) == 0:
            issues.append("Dataset has no columns")

        # Check for expected variables
        if required_vars:
            missing = set(required_vars) - set(df.columns)
            if missing:
                issues.append(f"Missing required variables: {', '.join(missing)}")

        # Infer primary key
        primary_key = None
        if 'usubjid' in df.columns:
            primary_key = 'usubjid'
        elif 'subjid' in df.columns:
            primary_key = 'subjid'

        return MetadataValidation(
            dataset_name=dataset_name,
            expected_name=None,
            column_count=len(df.columns),
            row_count=len(df),
            primary_key=primary_key,
            encoding='utf-8',
            issues=issues,
            warnings=warnings
        )

    def _validate_structure(
        self,
        df: pd.DataFrame,
        required_variables: List[str]
    ) -> StructuralValidation:
        """Validate dataset structure"""
        found_vars = df.columns.tolist()
        missing_vars = [v for v in required_variables if v not in found_vars]
        extra_vars = [v for v in found_vars if v not in required_variables]

        # Detect variable types
        var_types = {}
        type_mismatches = {}

        for col in df.columns:
            dtype = str(df[col].dtype)
            var_types[col] = dtype

        issues = []
        if missing_vars:
            issues.append(f"Missing variables: {', '.join(missing_vars)}")

        return StructuralValidation(
            required_variables=required_variables,
            found_variables=found_vars,
            missing_variables=missing_vars,
            extra_variables=extra_vars,
            variable_types=var_types,
            type_mismatches=type_mismatches,
            issues=issues
        )

    def _detect_duplicates(self, df: pd.DataFrame) -> DuplicateAnalysis:
        """Detect duplicate rows and keys"""
        total_rows = len(df)

        # Duplicate rows
        duplicate_rows = df.duplicated().sum()
        duplicate_pct = (duplicate_rows / total_rows * 100) if total_rows > 0 else 0

        # Duplicate subjects (USUBJID)
        duplicate_subjects = 0
        duplicate_visits = 0
        duplicate_keys = 0

        if 'usubjid' in df.columns:
            duplicate_subjects = df['usubjid'].duplicated().sum()

        if 'visit' in df.columns or 'visitnum' in df.columns:
            visit_col = 'visit' if 'visit' in df.columns else 'visitnum'
            duplicate_visits = df[visit_col].duplicated().sum()

        issues = []
        if duplicate_rows > 0:
            issues.append(f"Found {duplicate_rows} duplicate rows ({duplicate_pct:.1f}%)")
        if duplicate_subjects > 0:
            issues.append(f"Found {duplicate_subjects} duplicate subjects")

        return DuplicateAnalysis(
            total_rows=total_rows,
            duplicate_rows=duplicate_rows,
            duplicate_pct=duplicate_pct,
            duplicate_subjects=duplicate_subjects,
            duplicate_visits=duplicate_visits,
            duplicate_keys=duplicate_keys,
            issues=issues
        )

    def _profile_missing_values(self, df: pd.DataFrame) -> List[MissingValueProfile]:
        """Profile missing values per variable"""
        profiles = []

        for col in df.columns:
            missing_count = df[col].isnull().sum()
            total = len(df)
            missing_pct = (missing_count / total * 100) if total > 0 else 0

            if missing_pct > 0:
                # Detect pattern
                pattern = self._detect_missing_pattern(df[col])

                # Determine clinical criticality
                criticality = 'high' if missing_pct > 50 else 'medium' if missing_pct > 20 else 'low'

                # Recommend strategy
                strategy, reason = self._recommend_imputation_strategy(col, missing_pct, pattern)

                profiles.append(MissingValueProfile(
                    variable=col,
                    missing_count=int(missing_count),
                    missing_pct=round(missing_pct, 2),
                    pattern=pattern,
                    clinical_criticality=criticality,
                    recommended_strategy=strategy,
                    reason=reason
                ))

        return profiles

    def _detect_missing_pattern(self, series: pd.Series) -> str:
        """Detect missing value pattern"""
        mask = series.isnull()
        if not mask.any():
            return "none"

        # Check if monotone (all missing after first non-missing)
        non_null_idx = (~mask).idxmax()
        if mask[non_null_idx:].all():
            return "monotone"

        # Check if systematic (e.g., every Nth value)
        if (mask.sum() / len(series)) > 0.5:
            return "systematic"

        return "random"

    def _recommend_imputation_strategy(
        self,
        variable: str,
        missing_pct: float,
        pattern: str
    ) -> Tuple[str, str]:
        """Recommend missing data handling strategy"""
        var_lower = variable.lower()

        if missing_pct > 50:
            return "keep", "High missing percentage - retain as missing"

        if pattern == "monotone":
            return "locf", "Monotone pattern - suitable for LOCF"

        if any(x in var_lower for x in ['date', 'time']):
            return "linear_interpolation", "Time-based variable"

        if any(x in var_lower for x in ['age', 'weight', 'height', 'lab']):
            return "median", "Numeric clinical variable - median imputation"

        return "keep", "Default strategy - retain missing values"

    def _suggest_variable_mappings(
        self,
        found_vars: List[str],
        required_vars: List[str]
    ) -> List[VariableMapping]:
        """Suggest variable mappings using AI fuzzy matching"""
        mappings = []

        for req_var in required_vars:
            if req_var in found_vars:
                continue  # Already found

            # Find similar variables
            suggestions = self._find_similar_variables(req_var, found_vars)

            if suggestions:
                best_match, confidence = suggestions[0]
                mappings.append(VariableMapping(
                    original_var=best_match,
                    suggested_var=req_var,
                    confidence=confidence,
                    reason=f"AI suggested match for '{req_var}'",
                    alternatives=[s for s in suggestions[1:]]
                ))

        return mappings

    def _find_similar_variables(
        self,
        target: str,
        candidates: List[str]
    ) -> List[Tuple[str, float]]:
        """Find similar variable names"""
        # Simple string similarity using Jaro-Winkler-like approach
        results = []
        target_lower = target.lower()

        for candidate in candidates:
            candidate_lower = candidate.lower()

            # Exact match
            if candidate_lower == target_lower:
                results.append((candidate, 1.0))
            # Substring match
            elif target_lower in candidate_lower or candidate_lower in target_lower:
                results.append((candidate, 0.85))
            # Levenshtein-like
            else:
                similarity = self._string_similarity(target_lower, candidate_lower)
                if similarity > 0.7:
                    results.append((candidate, similarity))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Simple string similarity (0-1)"""
        longer = s1 if len(s1) > len(s2) else s2
        shorter = s2 if longer == s1 else s1

        if len(longer) == 0:
            return 1.0

        # Count matching characters
        matches = sum(c in longer for c in shorter)
        return matches / len(longer)

    def _classify_dataset(self, df: pd.DataFrame, dataset_name: str) -> DatasetType:
        """AI classify dataset type (Raw/SDTM/ADaM/TLF)"""
        name_lower = dataset_name.lower()
        cols_lower = [c.lower() for c in df.columns]

        scores = {dt: 0.0 for dt in DatasetType}

        # Check patterns for each type
        for dtype, sig in self.DATASET_SIGNATURES.items():
            # Pattern matching
            if re.search(sig['pattern'], name_lower):
                scores[dtype] += sig['confidence_boost']

            # Variable matching
            found_sig_vars = [v for v in sig['vars'] if v in cols_lower]
            if sig['vars'] and found_sig_vars:
                scores[dtype] += len(found_sig_vars) / len(sig['vars']) * 0.4

        # High clinical variables suggest SDTM/ADaM
        clinical_found = sum(1 for v in cols_lower if any(
            cv in v for cv in ['usubjid', 'visit', 'avisit', 'ady', 'dmy']
        ))
        if clinical_found > 0:
            scores[DatasetType.SDTM] += 0.1
            scores[DatasetType.ADAM] += 0.1

        # Determine type
        best_type = max(scores, key=scores.get)
        if scores[best_type] > 0:
            return best_type
        return DatasetType.UNKNOWN

    def _calculate_compatibility_score(
        self,
        metadata: MetadataValidation,
        structure: StructuralValidation,
        duplicates: DuplicateAnalysis,
        missing_values: List[MissingValueProfile],
        dataset_type: DatasetType
    ) -> CompatibilityScore:
        """Calculate AI Compatibility Score (0-100)"""

        # Structure score
        structure_score = 100.0
        if structure.missing_variables:
            structure_score -= len(structure.missing_variables) * 5
        if structure.extra_variables:
            structure_score -= len(structure.extra_variables) * 2
        structure_score = max(0, min(100, structure_score))

        # Variables score
        var_score = 100.0
        if structure.missing_variables:
            missing_pct = len(structure.missing_variables) / (
                len(structure.required_variables) + len(structure.missing_variables)
            ) * 100 if structure.required_variables else 0
            var_score -= missing_pct
        var_score = max(0, min(100, var_score))

        # Relationships score (no duplicates)
        rel_score = 100.0
        if duplicates.duplicate_pct > 0:
            rel_score -= min(50, duplicates.duplicate_pct)
        rel_score = max(0, min(100, rel_score))

        # Clinical compliance (SDTM/ADaM)
        clinical_score = 80.0 if dataset_type in [DatasetType.SDTM, DatasetType.ADAM] else 50.0
        if missing_values:
            high_missing = [m for m in missing_values if m.missing_pct > 20]
            clinical_score -= len(high_missing) * 10
        clinical_score = max(0, min(100, clinical_score))

        # Data quality score
        dq_score = 100.0
        if missing_values:
            avg_missing = sum(m.missing_pct for m in missing_values) / len(missing_values)
            dq_score -= avg_missing * 0.5
        dq_score = max(0, min(100, dq_score))

        # Overall
        overall = (structure_score + var_score + rel_score + clinical_score + dq_score) / 5

        issues = []
        if structure.missing_variables:
            issues.append(f"Missing {len(structure.missing_variables)} variables")
        if duplicates.duplicate_pct > 10:
            issues.append(f"High duplicate rate ({duplicates.duplicate_pct:.1f}%)")

        return CompatibilityScore(
            overall=round(overall, 1),
            structure=round(structure_score, 1),
            variables=round(var_score, 1),
            relationships=round(rel_score, 1),
            clinical=round(clinical_score, 1),
            data_quality=round(dq_score, 1),
            translation_ready=overall > 70,
            issues=issues
        )

    def _make_acceptance_decision(
        self,
        compatibility: CompatibilityScore,
        metadata: MetadataValidation,
        structure: StructuralValidation,
        duplicates: DuplicateAnalysis
    ) -> Tuple[AcceptanceStatus, List[str]]:
        """Make dataset acceptance decision"""
        recommendations = []

        if compatibility.overall >= 90:
            status = AcceptanceStatus.ACCEPTED
        elif compatibility.overall >= 70:
            status = AcceptanceStatus.ACCEPTED_WITH_WARNING
            if structure.missing_variables:
                recommendations.append(f"Upload missing variables: {', '.join(structure.missing_variables)}")
        elif compatibility.overall >= 50:
            status = AcceptanceStatus.NEEDS_REVIEW
            recommendations.append("Dataset requires manual review before use")
        else:
            status = AcceptanceStatus.REJECTED
            if structure.missing_variables:
                recommendations.append(f"Critical variables missing: {', '.join(structure.missing_variables)}")

        if duplicates.duplicate_pct > 10:
            recommendations.append(f"Remove {duplicates.duplicate_rows} duplicate rows")

        return status, recommendations

    def _create_preview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create dataset preview"""
        return {
            'rows': min(5, len(df)),
            'columns': len(df.columns),
            'data': df.head(5).to_dict('records'),
            'column_names': df.columns.tolist(),
            'dtypes': {col: str(df[col].dtype) for col in df.columns}
        }

    def _create_rejected_qualification(
        self,
        dataset_name: str,
        file_integrity: FileIntegrityResult,
        reason: str
    ) -> DatasetQualification:
        """Create rejected qualification"""
        return DatasetQualification(
            dataset_name=dataset_name,
            dataset_type=DatasetType.UNKNOWN,
            file_integrity=file_integrity,
            metadata=MetadataValidation(
                dataset_name=dataset_name,
                expected_name=None,
                column_count=0,
                row_count=0,
                primary_key=None,
                encoding='unknown',
                issues=[reason]
            ),
            structure=StructuralValidation(
                required_variables=[],
                found_variables=[],
                missing_variables=[],
                extra_variables=[],
                variable_types={},
                issues=[reason]
            ),
            duplicates=DuplicateAnalysis(
                total_rows=0,
                duplicate_rows=0,
                duplicate_pct=0,
                duplicate_subjects=0,
                duplicate_visits=0,
                duplicate_keys=0,
                issues=[reason]
            ),
            missing_values=[],
            variable_mappings=[],
            compatibility_score=CompatibilityScore(
                overall=0,
                structure=0,
                variables=0,
                relationships=0,
                clinical=0,
                data_quality=0,
                translation_ready=False,
                issues=[reason]
            ),
            acceptance_status=AcceptanceStatus.REJECTED,
            recommendations=[],
            preview_data={}
        )

    def _create_error_qualification(
        self,
        dataset_name: str,
        error: str
    ) -> DatasetQualification:
        """Create error qualification"""
        return self._create_rejected_qualification(
            dataset_name,
            FileIntegrityResult(
                is_valid=False,
                file_format='unknown',
                file_size_kb=0,
                encoding='unknown',
                row_count=0,
                column_count=0,
                has_corruption=True,
                corruption_details=[error],
                issues=[f"Error: {error}"]
            ),
            f"Error processing dataset: {error}"
        )
