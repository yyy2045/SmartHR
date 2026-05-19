<template>
  <AppLayout>
    <div class="page-header">
      <h2>知识库</h2>
      <el-button type="primary" @click="showUploadDialog = true">
        <el-icon><Upload /></el-icon> 上传文档
      </el-button>
    </div>

    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="8">
        <el-input v-model="searchQuery" placeholder="搜索知识库..." @keyup.enter="search">
          <template #append>
            <el-button :icon="Search" @click="search" />
          </template>
        </el-input>
      </el-col>
      <el-col :span="6">
        <el-select v-model="filterDocType" placeholder="按类型筛选" clearable>
          <el-option label="公司制度" value="POLICY" />
          <el-option label="操作手册" value="MANUAL" />
          <el-option label="历史记录" value="HISTORY" />
          <el-option label="其他" value="OTHER" />
        </el-select>
      </el-col>
    </el-row>

    <el-card v-if="searchResults.length">
      <template #header>
        <span>搜索结果</span>
        <el-button text @click="searchResults = []">清除</el-button>
      </template>
      <div v-for="(result, idx) in searchResults" :key="idx" class="search-result">
        <p class="result-content">{{ result.content }}</p>
        <div class="result-meta">
          <el-tag size="small">{{ result.docType }}</el-tag>
          <span class="similarity">{{ (result.similarity * 100).toFixed(1) }}% 匹配</span>
        </div>
      </div>
    </el-card>

    <el-card>
      <el-table :data="documents" v-loading="loading" style="width: 100%">
        <el-table-column prop="title" label="文档标题" />
        <el-table-column prop="filename" label="文件名" />
        <el-table-column prop="docType" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.docType }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="indexedStatus" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.indexedStatus)" size="small">
              {{ row.indexedStatus }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunks" label="块数" width="80" />
        <el-table-column prop="createdAt" label="创建时间" width="160" :formatter="formatDate" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="previewDoc(row)">预览</el-button>
            <el-button size="small" :loading="row.reindexing" @click="reindexDoc(row)">重新索引</el-button>
            <el-button size="small" type="danger" @click="deleteDoc(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchDocuments"
        @current-change="fetchDocuments"
        style="margin-top: 20px; justify-content: center"
      />
    </el-card>

    <el-dialog v-model="showUploadDialog" title="上传文档" width="500px">
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-width="100px">
        <el-form-item label="文档标题" prop="title">
          <el-input v-model="uploadForm.title" placeholder="文档标题" />
        </el-form-item>
        <el-form-item label="文档类型" prop="docType">
          <el-select v-model="uploadForm.docType" style="width: 100%">
            <el-option label="公司制度" value="POLICY" />
            <el-option label="操作手册" value="MANUAL" />
            <el-option label="历史记录" value="HISTORY" />
            <el-option label="其他" value="OTHER" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择文件" prop="file">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".pdf,.doc,.docx,.txt"
            :on-change="handleFileChange"
          >
            <el-button>选择文件</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="uploadDocument" :loading="uploading">上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showPreviewDialog" title="文档预览" width="700px">
      <div v-if="previewDocData" class="preview-content">
        <h3>{{ previewDocData.title }}</h3>
        <p class="preview-meta">
          <el-tag size="small">{{ previewDocData.docType }}</el-tag>
          <span>{{ previewDocData.chunks }} 块</span>
        </p>
        <el-divider />
        <p class="preview-text">{{ previewDocData.content || '暂无预览内容' }}</p>
      </div>
    </el-dialog>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import { getDocuments, uploadDocument as apiUploadDocument, deleteDocument, reindexDocument, searchKnowledge } from '@/api/knowledge'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Search } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const loading = ref(false)
const documents = ref([])
const searchResults = ref([])
const searchQuery = ref('')
const filterDocType = ref('')
const showUploadDialog = ref(false)
const showPreviewDialog = ref(false)
const uploading = ref(false)
const previewDocData = ref(null)
const uploadFormRef = ref()
const uploadRef = ref()

const selectedFile = ref(null)

const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

const uploadForm = reactive({
  title: '',
  docType: 'POLICY',
  file: null
})

const uploadRules = {
  title: [{ required: true, message: '请输入文档标题', trigger: 'blur' }],
  docType: [{ required: true, message: '请选择文档类型', trigger: 'change' }]
}

const formatDate = (row) => row.createdAt ? dayjs(row.createdAt).format('YYYY-MM-DD HH:mm') : '-'

const getStatusType = (status) => {
  if (status === 'INDEXED') return 'success'
  if (status === 'FAILED') return 'danger'
  return 'warning'
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
  uploadForm.title = file.name
}

const uploadDocument = async () => {
  if (!uploadFormRef.value) return
  await uploadFormRef.value.validate(async (valid) => {
    if (valid) {
      if (!selectedFile.value) {
        ElMessage.warning('请选择文件')
        return
      }
      uploading.value = true
      try {
        await apiUploadDocument(selectedFile.value, uploadForm.docType, 1)
        ElMessage.success('文档上传成功')
        showUploadDialog.value = false
        fetchDocuments()
      } catch (error) {
        // Error handled by interceptor
      } finally {
        uploading.value = false
      }
    }
  })
}

const fetchDocuments = async () => {
  loading.value = true
  try {
    const res = await getDocuments({ page: pagination.page - 1, size: pagination.size, companyId: 1, docType: filterDocType.value })
    documents.value = res?.content || res || []
    pagination.total = res?.totalElements || documents.value.length
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const search = async () => {
  if (!searchQuery.value) return
  try {
    searchResults.value = await searchKnowledge(searchQuery.value, 1)
  } catch (error) {
    ElMessage.error('搜索失败')
  }
}

const previewDoc = (row) => {
  previewDocData.value = row
  showPreviewDialog.value = true
}

const reindexDoc = async (row) => {
  row.reindexing = true
  try {
    await reindexDocument(row.id)
    ElMessage.success('重新索引已启动')
    setTimeout(fetchDocuments, 2000)
  } catch (error) {
    ElMessage.error('重新索引失败')
  } finally {
    row.reindexing = false
  }
}

const deleteDoc = async (row) => {
  try {
    await ElMessageBox.confirm(`删除"${row.title}"？`, '确认删除', { type: 'warning' })
    await deleteDocument(row.id)
    ElMessage.success('文档已删除')
    fetchDocuments()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(fetchDocuments)
</script>

<style scoped>
.search-result {
  padding: 12px 0;
  border-bottom: 1px solid #e4e7ed;
}

.search-result:last-child {
  border-bottom: none;
}

.result-content {
  margin-bottom: 8px;
  line-height: 1.6;
}

.result-meta {
  display: flex;
  gap: 12px;
  align-items: center;
}

.similarity {
  font-size: 12px;
  color: #67c23a;
}

.preview-content h3 {
  margin-bottom: 8px;
}

.preview-meta {
  display: flex;
  gap: 12px;
  align-items: center;
  color: #909399;
  font-size: 13px;
}

.preview-text {
  line-height: 1.8;
  white-space: pre-wrap;
}
</style>