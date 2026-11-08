use pyo3::prelude::*;

#[pymodule]
mod rust_sha256 {
    use pyo3::prelude::*;
    use sha2::{Digest, Sha256};

    #[pyfunction]
    fn calculate_sha(data: &[u8]) -> PyResult<String> {
        let mut hasher = Sha256::new();

        hasher.update(data);

        let hash = hasher.finalize();

        Ok(hex::encode(hash))
    }
}
