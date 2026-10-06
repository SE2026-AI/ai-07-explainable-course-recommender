# API samples (TestClient, catalog-demo-v1, request bodies from docs/architecture/contracts/examples)

## BASE recommendation (success)

`POST /v1/recommendations` → **HTTP 200**

```json
{
 "request_id": "req-289b56b4ba2d",
 "contract_version": "0.1.0",
 "catalog_version": "catalog-demo-v1",
 "algorithm_version": "rank-0.1",
 "normalization_policy": "renormalize-over-available-components",
 "weights": {
  "goal_match": 0.5,
  "interest_match": 0.2,
  "preparation": 0.1,
  "workload_fit": 0.2
 },
 "term_id": "2027-FALL",
 "status": "ok",
 "comparable_candidate_set_id": "sha256:ceca19e855c1464e04fc9f7f0d6f0643158ccfb54fefac796e236176e33c7f68",
 "eligible": [
  {
   "course_id": "ST201",
   "rank": 1,
   "score": 0.7777777777777779,
   "score_percent": 77.8,
   "reason_codes": [
    "GOAL_MATCH",
    "INTEREST_MATCH",
    "WORKLOAD_FIT",
    "CONDITIONALLY_UNLOCKABLE"
   ],
   "reasons": [
    {
     "code": "GOAL_MATCH",
     "text": "Phù hợp mục tiêu Machine Learning Engineer (mức liên quan 100%, đóng góp 56% vào điểm).",
     "evidence_refs": [
      {
       "source": "catalog-demo-v1",
       "record_id": "ST201"
      },
      {
       "source": "catalog-demo-v1",
       "record_id": "goal:ML_ENGINEER"
      }
     ],
     "component": "goal_match"
    },
    {
     "code": "INTEREST_MATCH",
     "text": "Trùng sở thích: DATA (đóng góp 11%).",
     "evidence_refs": [
      {
       "source": "catalog-demo-v1",
       "record_id": "ST201"
      },
      {
       "source": "profile",
       "record_id": "interest:DATA"
      }
     ],
     "component": "interest_match"
    },
    {
     "code": "WORKLOAD_FIT",
     "text": "Khối lượng ~6 giờ/tuần, hợp với ngân sách 12 giờ/tuần.",
     "evidence_refs": [
      {
       "source": "catalog-demo-v1",
       "record_id": "ST201"
      },
      {
       "source": "profile",
       "record_id": "workload_preference"
      }
     ],
     "component": "workload_fit"
    },
    {
     "code": "CONDITIONALLY_UNLOCKABLE",
     "text": "Qua môn này sẽ mở khóa: AI301.",
     "evidence_refs": [
      {
       "source": "catalog-demo-v1",
       "record_id": "AI301"
      }
     ]
    }
   ]
  },
  {
   "course_id": "SE201",
   "rank": 2,
   "score": 0.42592592592592593,
   "score_percent": 42.6,
   "reason_codes": [
    "GOAL_MATCH",
    "WORKLOAD_FIT"
   ],
   "reasons": [
    {
     "code": "GOAL_MATCH",
     "text": "Phù hợp mục tiêu Machine Learning Engineer (mức liên quan 50%, đóng góp 28% vào điểm).",
     "evidence_refs": [
      {
       "source": "catalog-demo-v1",
       "record_id": "SE201"
      },
      {
       "source": "catalog-demo-v1",
       "record_id": "goal:ML_ENGINEER"
      }
   
```

## Why-not AI301 blocked / ST201 eligible

`POST /v1/why-not` → **HTTP 200**

```json
{
 "request_id": "req-25d485a8ce49",
 "contract_version": "0.1.0",
 "catalog_version": "catalog-demo-v1",
 "algorithm_version": "rank-0.1",
 "results": [
  {
   "course_id": "AI301",
   "eligible": false,
   "direct_missing_prerequisite_ids": [
    "ST201"
   ],
   "transitive_missing_paths": [
    [
     "ST201",
     "AI301"
    ]
   ],
   "reason_codes": [
    "MISSING_PREREQUISITE"
   ],
   "reasons": [
    {
     "code": "MISSING_PREREQUISITE",
     "text": "Chưa qua môn tiên quyết bắt buộc: ST201.",
     "evidence_refs": [
      {
       "source": "catalog-demo-v1",
       "record_id": "AI301"
      },
      {
       "source": "catalog-demo-v1",
       "record_id": "ST201"
      }
     ]
    }
   ],
   "evidence_refs": [
    {
     "source": "catalog-demo-v1",
     "record_id": "AI301"
    },
    {
     "source": "catalog-demo-v1",
     "record_id": "ST201"
    }
   ]
  },
  {
   "course_id": "ST201",
   "eligible": true,
   "direct_missing_prerequisite_ids": [],
   "transitive_missing_paths": [],
   "rank": 1,
   "score": 0.8571428571428572,
   "score_percent": 85.7,
   "reason_codes": [
    "GOAL_MATCH",
    "WORKLOAD_FIT",
    "CONDITIONALLY_UNLOCKABLE"
   ],
   "reasons": [
    {
     "code": "GOAL_MATCH",
     "text": "Phù hợp mục tiêu Machine Learning Engineer (mức liên quan 100%, đóng góp 71% vào điểm).",
     "evidence_refs": [
      {
       "source": "catalog-demo-v1",
       "record_id": "ST201"
      },
      {
       "source": "catalog-demo-v1",
       "record_id": "goal:ML_ENGINEER"
      }
     ],
     "component": "goal_match"
    },
    {
     "code": "WORKLOAD_FIT",
     "text": "Khối lượng ~6 giờ/tuần, hợp với ngân sách 12 giờ/tuần.",
     "evidence_refs": [
      {
       "source": "catalog-demo-v1",
       "record_id": "ST201"
      },
      {
       "source": "profile",
       "record_id": "workload_preference"
      }
     ],
     "component": "workload_fit"
    },
    {
     "code": "CONDITIONALLY_UNLOCKABLE",
     "text": "Qua môn này sẽ mở khóa: AI301.",
     "evidence_refs": [
      {
       "source": "catalog-demo-v1",
       "record_id": "AI301"
      }
     ]
    }
   ],
   "evidence_refs": [
    {
     "source": "catalog-demo-v1",
     "record_id": "ST201"
    },
    {
     "source": "catalog-demo-v1",
     "record_id": "goal:ML_ENGINEER"
    },
    {
     "source": "profile",
     "record_id": "workload_preference"
    },
    {
     "source": "catalog-demo-v1",
     "record_id": "AI301"
    }
   ]
  }
 ]
}
```

## What-if: hypothetical ST201 + light weights

`POST /v1/simulations` → **HTTP 200**

```json
{
 "request_id": "req-4068a51ca3b0",
 "contract_version": "0.1.0",
 "catalog_version": "catalog-demo-v1",
 "algorithm_version": "rank-0.1",
 "baseline_version": "base-v1",
 "baseline_digest": "sha256:8a8bcfb965b0d5dc242e334356669c3f4b452471fa928f17d4188fff3d3cca06",
 "scenario_id": "whatif-light",
 "scenario_version": "1",
 "comparable_candidate_set_id": "sha256:cb8132e14b7d9c5939a93d8a298bc45b3915204b2717f9d287b99bda866fce6e",
 "baseline": {
  "weights": {
   "goal_match": 0.8,
   "interest_match": 0.0,
   "preparation": 0.0,
   "workload_fit": 0.2
  },
  "eligible_course_ids": [
   "SE201",
   "ST201"
  ],
  "scores": {
   "ST201": 0.9,
   "SE201": 0.5333333333333334
  },
  "ranks": {
   "ST201": 1,
   "SE201": 2
  },
  "comparable_candidate_set_id": "sha256:ceca19e855c1464e04fc9f7f0d6f0643158ccfb54fefac796e236176e33c7f68"
 },
 "scenario": {
  "weights": {
   "goal_match": 0.2,
   "interest_match": 0.0,
   "preparation": 0.0,
   "workload_fit": 0.8
  },
  "eligible_course_ids": [
   "AI301",
   "SE201"
  ],
  "scores": {
   "SE201": 0.6333333333333334,
   "AI301": 0.46666666666666673
  },
  "ranks": {
   "SE201": 1,
   "AI301": 2
  },
  "comparable_candidate_set_id": "sha256:dfbd30e395e64af5135438f5aab5348cab2c066177debf7aa359156edd31289f"
 },
 "changes": [
  {
   "course_id": "SE201",
   "rank_before": 1,
   "rank_after": 1,
   "score_before": 0.5333333333333334,
   "score_after": 0.6333333333333334,
   "score_delta": 0.09999999999999998
  }
 ],
 "entered": [
  "AI301"
 ],
 "exited": [
  "ST201"
 ]
}
```

## Invalid weights (all zero)

`POST /v1/recommendations` → **HTTP 422**

```json
{
 "request_id": "req-830d0fac3686",
 "contract_version": "0.1.0",
 "error": {
  "code": "INVALID_WEIGHTS",
  "message": "at least one weight must be positive",
  "retryable": false
 }
}
```

## Unknown catalog version

`GET /v1/catalog/graph?catalog_version=catalog-old` → **HTTP 409**

```json
{
 "request_id": "req-00fcf5c537ea",
 "contract_version": "0.1.0",
 "error": {
  "code": "CATALOG_VERSION_UNKNOWN",
  "message": "Unknown or stale catalog version; refresh and retry.",
  "retryable": false,
  "details": {
   "requested": "catalog-old",
   "available_versions": [
    "catalog-demo-v1",
    "catalog-synthetic-v1"
   ]
  }
 }
}
```

## Injected catalog outage

`POST /v1/recommendations` with header `{'x-ai07-fault': 'catalog_unavailable'}` → **HTTP 503**

```json
{
 "request_id": "req-f570bfc998ba",
 "contract_version": "0.1.0",
 "error": {
  "code": "CATALOG_UNAVAILABLE",
  "message": "The requested catalog snapshot is unavailable.",
  "retryable": true,
  "details": {
   "catalog_version": "catalog-demo-v1"
  }
 }
}
```

